"""
Fon Tarayıcı - Backend API v2
Yeni mimari: TEFAS önce, PDF opsiyonel
Port: 9009
"""

import os, json, asyncio, subprocess, urllib.request, urllib.parse
import httpx
import requests as _requests
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger, timedelta
from pathlib import Path
from typing import Optional

import anthropic
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker, mapped_column, Mapped
from sqlalchemy import String, Float, Integer, Text, Date, DateTime, select, delete, desc
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "fon.db"
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
_cache: dict = {}



class Base(DeclarativeBase):
    pass


class FundRecord(Base):
    __tablename__ = "fund_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(String(20), index=True)
    fund_name: Mapped[str] = mapped_column(String(300))
    date_key: Mapped[str] = mapped_column(String(10), index=True)
    month_key: Mapped[str] = mapped_column(String(7), index=True)
    unit_price: Mapped[float] = mapped_column(Float)
    total_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    participant_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    share_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    portfolio_items: Mapped[str] = mapped_column(Text, default="[]")
    has_pdf_analysis: Mapped[int] = mapped_column(Integer, default=0)
    monthly_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    yearly_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_maturity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    monthly_turnover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_holdings: Mapped[str] = mapped_column(Text, default="[]")
    expenses: Mapped[str] = mapped_column(Text, default="{}")
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stopaj_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fund_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ai_insights: Mapped[str] = mapped_column(Text, default="[]")
    dexter_recommendations: Mapped[str] = mapped_column(Text, default="[]")
    twitter_summary: Mapped[str] = mapped_column(Text, default="")
    raw_pdf_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    published: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)


class EvolverMemory(Base):
    __tablename__ = "evolver_memory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(String(20), index=True)
    memory_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    snapshot_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


app = FastAPI(title="Fon Tarayıcı API v2")
scheduler = AsyncIOScheduler()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database hazır:", DB_PATH)
    loop = asyncio.get_running_loop()


# ─── TEFAS ─────────────────────────────────────────────────────────────────────



def _post(endpoint: str, payload: dict) -> dict:
    url = f"https://www.tefas.gov.tr/api/DB/{endpoint}"
    r = _requests.post(url, data=payload, timeout=15)
    if not r.text.strip() or r.text.strip().startswith("<"):
        raise ValueError(f"WAF/bos yanit: {r.text[:80]}")
    return r.json()


def _ts_to_date(ts) -> str:
    try:
        ms = int(str(ts).replace(",", "").split(".")[0])
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except Exception:
        return ""


ALLOC_MAP = {
    "HS": ("Hisse Senedi", "equity"), "YHS": ("Yabancı Hisse", "equity"),
    "TPP": ("Tahvil/Bono TPP", "bond"), "BPP": ("Tahvil/Bono BPP", "bond"),
    "DB": ("Devlet Borçlanma", "bond"), "OST": ("Özel Sektör Tahvili", "bond"),
    "FB": ("Finansman Bonosu", "bond"), "R": ("Repo", "repo"), "TR": ("Ters Repo", "repo"),
    "VM": ("Vadesiz Mevduat", "deposit"), "VDM": ("Vadeli Mevduat", "deposit"),
    "VMTL": ("Mevduat TL", "deposit"), "YYF": ("Yatırım Fonu", "fund"),
    "BYF": ("Borsa YF", "fund"), "KM": ("Kıymetli Maden", "commodity"),
    "KHAU": ("Altın", "commodity"), "GSYKB": ("Girişim Sermayesi", "other"),
    "VİNT": ("Varant", "other"), "T": ("Teminat", "other"),
}


def _parse_alloc(row: dict) -> list:
    items = []
    for f, (name, cat) in ALLOC_MAP.items():
        v = row.get(f)
        if v and float(v) > 0.01:
            items.append({"name": name, "value": round(float(v), 2), "category": cat})
    return sorted(items, key=lambda x: -x["value"])


async def _tefas_history(fund_code: str, days: int = 365) -> list:
    script = str(Path(__file__).parent / "tefas_fetch.py")
    all_data = []
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    chunk_days = 60
    cursor = start_dt
    while cursor < end_dt:
        chunk_end = min(cursor + timedelta(days=chunk_days), end_dt)
        s = cursor.strftime('%d.%m.%Y')
        e = chunk_end.strftime('%d.%m.%Y')
        try:
            result = await asyncio.to_thread(subprocess.run,
                ["python3", script, "BindHistoryInfo", fund_code, s, e],
                capture_output=True, text=True, timeout=30)
            if result.stdout and not result.stdout.strip().startswith("<"):
                all_data.extend(json.loads(result.stdout).get("data", []))
        except Exception as ex:
            print(f"⚠️  TEFAS chunk ({fund_code} {s}-{e}): {ex}")
        cursor = chunk_end + timedelta(days=1)
        import time; time.sleep(0.3)
    return all_data


async def _tefas_alloc(fund_code: str, days: int = 60) -> dict:
    end_str = datetime.now().strftime('%d.%m.%Y')
    start_str = (datetime.now() - timedelta(days=days)).strftime('%d.%m.%Y')
    script = str(Path(__file__).parent / "tefas_fetch.py")
    try:
        result = await asyncio.to_thread(subprocess.run,
            ["python3", script, "BindHistoryAllocation", fund_code, start_str, end_str],
            capture_output=True, text=True, timeout=30)
        if not result.stdout or result.stdout.strip().startswith("<"):
            return {}
        out = {}
        for row in json.loads(result.stdout).get("data", []):
            d = _ts_to_date(row.get("TARIH", ""))
            if d:
                out[d] = _parse_alloc(row)
        return out
    except Exception as e:
        print(f"⚠️  TEFAS alloc ({fund_code}): {e}")
        return {}


# ─── EVOLVER ───────────────────────────────────────────────────────────────────

async def _update_evolver(session: AsyncSession, fund_code: str, rows: list):
    import math
    prices = [r["unit_price"] for r in rows if r.get("unit_price", 0) > 0]
    if len(prices) < 10:
        return

    # Günlük getiriler
    all_returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices)) if prices[i-1] > 0]
    recent30 = prices[-30:]
    ret30 = [(recent30[i] - recent30[i-1]) / recent30[i-1] * 100 for i in range(1, len(recent30)) if recent30[i-1] > 0]

    avg_d = sum(ret30) / len(ret30) if ret30 else 0

    # Standart sapma (gerçek volatilite)
    mean_r = sum(all_returns) / len(all_returns) if all_returns else 0
    variance = sum((r - mean_r) ** 2 for r in all_returns) / len(all_returns) if all_returns else 0
    std_dev = math.sqrt(variance)
    ann_vol = round(std_dev * math.sqrt(252), 2)  # Yıllık volatilite

    # Max drawdown
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Sharpe (risksiz oran %45 → günlük ~0.123%)
    risk_free_daily = 45 / 252
    excess = [r - risk_free_daily for r in all_returns]
    sharpe = (sum(excess) / len(excess)) / std_dev * math.sqrt(252) if std_dev > 0 else 0

    # Pozitif gün oranı
    pos_days = sum(1 for r in all_returns if r > 0)
    pos_ratio = round(pos_days / len(all_returns) * 100, 1) if all_returns else 0

    # En iyi / en kötü ay (aylık getiri)
    monthly = {}
    for r in rows:
        if r.get("unit_price", 0) > 0:
            ym = r["date_key"][:7]
            monthly.setdefault(ym, []).append(r["unit_price"])
    monthly_returns = {}
    for ym, ps in monthly.items():
        if len(ps) >= 2:
            monthly_returns[ym] = (ps[-1] - ps[0]) / ps[0] * 100
    best_month = max(monthly_returns.items(), key=lambda x: x[1]) if monthly_returns else None
    worst_month = min(monthly_returns.items(), key=lambda x: x[1]) if monthly_returns else None

    # Trend gücü (son 30 vs önceki 30)
    prev30 = prices[-60:-30] if len(prices) >= 60 else prices[:len(prices)//2]
    prev_avg = sum(prev30) / len(prev30) if prev30 else prices[0]
    curr_avg = sum(recent30) / len(recent30) if recent30 else prices[-1]
    momentum = round((curr_avg - prev_avg) / prev_avg * 100, 2) if prev_avg > 0 else 0

    content = json.dumps({
        "avg_daily_return": round(avg_d, 4),
        "trend": "yukarı" if prices[-1] > prices[0] else "aşağı",
        "volatility_range": round(max(ret30) - min(ret30), 2) if ret30 else 0,
        "volatility_std": round(std_dev, 4),
        "annual_volatility": ann_vol,
        "max_drawdown": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "positive_days_pct": pos_ratio,
        "momentum_30d": momentum,
        "best_month": {"month": best_month[0], "return": round(best_month[1], 2)} if best_month else None,
        "worst_month": {"month": worst_month[0], "return": round(worst_month[1], 2)} if worst_month else None,
        "sample_count": len(prices),
        "latest_price": round(prices[-1], 6),
        "total_return": round((prices[-1] - prices[0]) / prices[0] * 100, 2),
    }, ensure_ascii=False)

    today = datetime.utcnow().date()

    # Bugün zaten snapshot var mı?
    ex = await session.execute(select(EvolverMemory).where(
        EvolverMemory.fund_code == fund_code,
        EvolverMemory.memory_type == "price_pattern",
        EvolverMemory.snapshot_date == today))
    existing_today = ex.scalar_one_or_none()

    if existing_today:
        # Bugünkü kaydı güncelle
        existing_today.content = content
        existing_today.last_seen = datetime.utcnow()
    else:
        # Yeni snapshot ekle
        session.add(EvolverMemory(
            fund_code=fund_code,
            memory_type="price_pattern",
            content=content,
            confidence=0.5,
            snapshot_date=today,
        ))

    # Tüm geçmiş snapshot'ları al → sinyal üret
    all_ex = await session.execute(select(EvolverMemory).where(
        EvolverMemory.fund_code == fund_code,
        EvolverMemory.memory_type == "price_pattern"
    ).order_by(EvolverMemory.snapshot_date))
    all_snaps = all_ex.scalars().all()

    if len(all_snaps) >= 3:
        snapdata = []
        for s in all_snaps:
            try: snapdata.append(json.loads(s.content))
            except: pass

        # Sharpe trendi
        sharpes = [d.get("sharpe_ratio") for d in snapdata if d.get("sharpe_ratio") is not None]
        sharpe_trend = "artıyor" if len(sharpes) >= 2 and sharpes[-1] > sharpes[-2] else "azalıyor" if len(sharpes) >= 2 else "belirsiz"

        # Momentum trendi
        moms = [d.get("momentum_30d") for d in snapdata if d.get("momentum_30d") is not None]
        mom_trend = "güçleniyor" if len(moms) >= 2 and moms[-1] > moms[-2] else "zayıflıyor" if len(moms) >= 2 else "belirsiz"

        # Volatilite trendi
        vols = [d.get("annual_volatility") for d in snapdata if d.get("annual_volatility") is not None]
        vol_trend = "artıyor" if len(vols) >= 2 and vols[-1] > vols[-2] else "azalıyor" if len(vols) >= 2 else "belirsiz"

        # Drawdown trendi
        dds = [d.get("max_drawdown") for d in snapdata if d.get("max_drawdown") is not None]
        dd_trend = "kötüleşiyor" if len(dds) >= 2 and dds[-1] > dds[-2] else "iyileşiyor" if len(dds) >= 2 else "belirsiz"

        # Sinyal üret
        signals = []
        curr = snapdata[-1]
        if curr.get("sharpe_ratio", 0) >= 1.5 and sharpe_trend == "artıyor":
            signals.append({"type": "pozitif", "msg": f"Sharpe {curr['sharpe_ratio']:.2f} ve artıyor — risk/getiri dengesi güçlü"})
        elif curr.get("sharpe_ratio", 0) < 0:
            signals.append({"type": "negatif", "msg": f"Sharpe negatif ({curr['sharpe_ratio']:.2f}) — getiri risksiz oranın altında"})
        if mom_trend == "güçleniyor" and curr.get("momentum_30d", 0) > 5:
            signals.append({"type": "pozitif", "msg": f"Momentum güçleniyor (+{curr['momentum_30d']:.1f}%) — kısa vadeli ivme artıyor"})
        elif mom_trend == "zayıflıyor" and curr.get("momentum_30d", 0) < -3:
            signals.append({"type": "negatif", "msg": f"Momentum zayıflıyor ({curr['momentum_30d']:.1f}%) — dikkat"})
        if vol_trend == "artıyor" and curr.get("annual_volatility", 0) > 50:
            signals.append({"type": "uyarı", "msg": f"Volatilite artıyor (%{curr['annual_volatility']:.1f}) — risk yükseliyor"})
        if dd_trend == "iyileşiyor":
            signals.append({"type": "pozitif", "msg": f"Max drawdown iyileşiyor (%{curr['max_drawdown']:.1f}) — toparlanma sinyali"})
        if curr.get("positive_days_pct", 0) > 55:
            signals.append({"type": "pozitif", "msg": f"Pozitif gün oranı yüksek (%{curr['positive_days_pct']:.1f}) — tutarlı getiri"})

        signal_content = json.dumps({
            "sharpe_trend": sharpe_trend,
            "momentum_trend": mom_trend,
            "volatility_trend": vol_trend,
            "drawdown_trend": dd_trend,
            "snapshot_count": len(all_snaps),
            "signals": signals,
            "last_sharpe": sharpes[-1] if sharpes else None,
            "last_momentum": moms[-1] if moms else None,
            "last_vol": vols[-1] if vols else None,
        }, ensure_ascii=False)

        # signal kaydını güncelle/ekle
        sig_ex = await session.execute(select(EvolverMemory).where(
            EvolverMemory.fund_code == fund_code,
            EvolverMemory.memory_type == "signal"))
        sig_rec = sig_ex.scalar_one_or_none()
        if sig_rec:
            sig_rec.content = signal_content
            sig_rec.occurrence_count += 1
            sig_rec.confidence = min(0.99, sig_rec.confidence + 0.05)
            sig_rec.last_seen = datetime.utcnow()
        else:
            session.add(EvolverMemory(
                fund_code=fund_code,
                memory_type="signal",
                content=signal_content,
                confidence=0.5,
                snapshot_date=today,
            ))


# ─── CLAUDE ────────────────────────────────────────────────────────────────────

def _extract_pdf(pdf_bytes: bytes) -> str:
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(p.get_text() for p in doc)
    doc.close()
    return text[:20000]


async def _analyze(pdf_text: str, fund_code: str, tefas_ctx: dict, history: list, evolver: list) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY bulunamadı")

    ev_str = ""
    for m in evolver:
        if m.memory_type == "price_pattern":
            try:
                p = json.loads(m.content)
                ev_str = f"\nEVOLVER: trend={p['trend']}, avg_daily={p['avg_daily_return']}%, vol={p['volatility']}%, n={p['sample_count']}"
            except Exception:
                pass

    hist_str = ""
    if history:
        hist_str = "\nSON GEÇMİŞ:\n" + "\n".join(
            f"- {r['date_key']}: {r['unit_price']:.6f} TL, ₺{(r.get('total_value',0)/1e6):.1f}M"
            for r in history[-10:])

    t = tefas_ctx
    tc_str = f"\nGÜNCEL TEFAS: {t.get('price',0):.6f} TL, ₺{(t.get('total_value',0)/1e6):.1f}M, {int(t.get('participants',0)):,} yatırımcı" if t else ""

    prompt = f"""KAP yatırım fonu aylık raporu. SADECE JSON döndür.
{tc_str}{hist_str}{ev_str}

ÖNEMLİ KURALLAR:
- managementFee: "AY İÇİNDE YAPILAN GİDERLER" tablosunu bul. (1) "Fon Yönetim Ücreti" satırında ORAN% sütunu varsa (örn: 0.2316%) o değeri × 12 = yıllık oran. (2) ORAN% yoksa sadece tutar varsa: Tutar ÷ Fon Toplam Değeri × 100 × 12. (3) Hiçbiri yoksa 1.75 yaz.
- custodyFee: Aynı tablodan "Portföydeki Varlıkların Saklanması" satırı. ORAN% varsa × 12. Yoksa Tutar ÷ FTD × 100 × 12. Bulamazsan 0.09 yaz.
- totalExpenseRatio: Aynı tablonun TOPLAM satırındaki ORAN% × 12. Yoksa tüm satır oranlarını topla × 12. Bulamazsan 0.22 yaz.
- expenses alanını ASLA boş bırakma, her zaman sayısal değer yaz.
- custodyFee: saklama ücreti YILLIK oran (%)
- totalExpenseRatio: PDF'deki toplam gider oranı (ORAN% sütunundaki toplam × 12)
- stopajRate: TEFAS'ta yazan stopaj oranı (örn: 17.5). PDF'te yoksa 17.5 kullan.
- valor: TEFAS'taki alış/satış valörü (örn: "T+1/T+2"). PDF'te yoksa "T+1/T+2" kullan.
- monthlyReturn: "Aylık Pay Fiyatı Artış Oranı" (%)
- yearlyReturn: "Yıllık Pay Fiyatı Artış Oranı" (%)
- twitterSummary: Aşağıdaki formatı kullan, tüm değerleri PDF'ten gerçek verilerle doldur:
  📊 [FONKOD] | [FON ADI KISA]
  ━━━━━━━━━━━━━━
  🚀 Aylık: +X.XX% | Yıllık: +XX.XX%
  💼 Portföy: ₺XXXm | XXX yatırımcı
  ⚠️ Risk: X/7 · [Düşük/Orta/Yüksek]
  
  🔍 Öne Çıkanlar:
  • [PDF'den önemli portföy bilgisi 1]
  • [PDF'den önemli portföy bilgisi 2]
  • [PDF'den önemli portföy bilgisi 3]
  
  📅 [Ay Yıl] · KAP Raporu
  #[SektörTag] #KAP #YatırımFonu #TEFAS

PDF:
{pdf_text}

JSON (başka hiçbir şey yazma):
{{"fundCode":"{fund_code}","fundName":"...","company":"...","month":"Ocak 2026","monthKey":"2026-01","monthlyReturn":8.19,"yearlyReturn":74.24,"avgMaturity":39.98,"monthlyTurnover":1.65,"topHoldings":[{{"name":"AKBNK","fullName":"Akbank T.A.Ş.","weight":5.5}}],"expenses":{{"managementFee":1.75,"custodyFee":0.0917,"totalExpenseRatio":0.2208}},"riskScore":4,"stopajRate":17.5,"valor":"T+1/T+2","fundType":"Değişken Fon","portfolioItems":[{{"name":"Hisse Senedi","value":40.0,"category":"equity"}}],"aiInsights":["Tespit 1","Tespit 2","Tespit 3"],"dexterRecommendations":["TEFAS+evolver'a dayalı öneri 1","Öneri 2","Öneri 3"],"twitterSummary":"📊 URA | ATA PORTFÖY ENERJİ DEĞİŞKEN FON\n━━━━━━━━━━━━━━\n🚀 Aylık: +27.06% | Yıllık: +95.55%\n💼 Portföy: ₺939.8M | 12.832 yatırımcı\n⚠️ Risk: 5/7 · Orta-Yüksek\n\n🔍 Öne Çıkanlar:\n• %63 yabancı uranyum hisseleri\n• Güçlü momentum, hacim artışı\n• Enflasyona karşı alternatif varlık\n\n📅 Ocak 2026 · KAP Raporu\n#Enerji #Uranyum #KAP #YatırımFonu #TEFAS"}}"""

    client = anthropic.Anthropic(api_key=api_key)
    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(None, lambda: client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    ))
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip().rstrip("```").strip())


# ─── API ROUTES ────────────────────────────────────────────────────────────────

@app.post("/api/funds/track")
async def track_fund(payload: dict = Body(...)):
    """Fon kodu gir → TEFAS'tan 365 günlük veri çek, DB'ye kaydet"""
    fund_code = payload.get("fundCode", "").upper().strip()
    if not fund_code:
        raise HTTPException(400, "fundCode gerekli")

    rows = await _tefas_history(fund_code, days=365)
    if not rows:
        raise HTTPException(404, f"TEFAS'ta {fund_code} bulunamadı")

    alloc = await _tefas_alloc(fund_code, days=60)
    fund_name = rows[0].get("FONUNVAN", fund_code)

    async with AsyncSessionLocal() as session:
        existing = set(r[0] for r in (await session.execute(
            select(FundRecord.date_key).where(FundRecord.fund_code == fund_code)
        )).fetchall())

        new_count = 0
        all_rows = []
        for row in rows:
            d = _ts_to_date(row.get("TARIH", ""))
            if not d:
                continue
            price = float(row.get("FIYAT", 0))
            tv = float(row.get("PORTFOYBUYUKLUK", 0))
            all_rows.append({"date_key": d, "unit_price": price, "total_value": tv})
            if d in existing:
                continue
            session.add(FundRecord(
                fund_code=fund_code, fund_name=fund_name,
                date_key=d, month_key=d[:7],
                unit_price=price, total_value=tv,
                participant_count=float(row.get("KISISAYISI", 0)),
                share_count=float(row.get("TEDPAYSAYISI", 0)),
                portfolio_items=json.dumps(alloc.get(d, []), ensure_ascii=False),
            ))
            new_count += 1

        await session.commit()
        await _update_evolver(session, fund_code, all_rows)
        await session.commit()

    return {"success": True, "fundCode": fund_code, "fundName": fund_name,
            "totalRows": len(rows), "newRows": new_count}


@app.post("/api/funds/{fund_code}/refresh")
async def refresh_fund(fund_code: str):
    """Son 7 günü TEFAS'tan güncelle"""
    fund_code = fund_code.upper()
    rows = await _tefas_history(fund_code, days=7)
    if not rows:
        raise HTTPException(404, "TEFAS'tan veri alınamadı")
    alloc = await _tefas_alloc(fund_code, days=10)
    fund_name = rows[0].get("FONUNVAN", fund_code)
    async with AsyncSessionLocal() as session:
        existing = set(r[0] for r in (await session.execute(
            select(FundRecord.date_key).where(FundRecord.fund_code == fund_code)
        )).fetchall())
        new_count = 0
        for row in rows:
            d = _ts_to_date(row.get("TARIH", ""))
            if not d or d in existing:
                continue
            session.add(FundRecord(
                fund_code=fund_code, fund_name=fund_name,
                date_key=d, month_key=d[:7],
                unit_price=float(row.get("FIYAT", 0)),
                total_value=float(row.get("PORTFOYBUYUKLUK", 0)),
                participant_count=float(row.get("KISISAYISI", 0)),
                share_count=float(row.get("TEDPAYSAYISI", 0)),
                portfolio_items=json.dumps(alloc.get(d, []), ensure_ascii=False),
            ))
            new_count += 1
        await session.commit()
    return {"success": True, "fundCode": fund_code, "newRows": new_count}


@app.post("/api/funds/{fund_code}/analyze-pdf")
async def analyze_pdf(fund_code: str, file: UploadFile = File(...)):
    """PDF yükle → Claude analizi → ilgili TEFAS kaydını zenginleştir"""
    fund_code = fund_code.upper()
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Sadece PDF")
    pdf_bytes = await file.read()
    pdf_text = _extract_pdf(pdf_bytes)
    if len(pdf_text.strip()) < 100:
        raise HTTPException(422, "PDF'den metin çıkarılamadı")

    async with AsyncSessionLocal() as session:
        latest = (await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code)
            .order_by(desc(FundRecord.date_key)).limit(1)
        )).scalar_one_or_none()
        if not latest:
            raise HTTPException(404, f"{fund_code} için önce 'Fon Ekle' ile TEFAS verisi çekin")

        history_records = (await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code).order_by(FundRecord.date_key)
        )).scalars().all()
        history = [{"date_key": r.date_key, "unit_price": r.unit_price, "total_value": r.total_value}
                   for r in history_records]
        evolver = await (async_get_evolver := session.execute(
            select(EvolverMemory).where(EvolverMemory.fund_code == fund_code).order_by(EvolverMemory.confidence.desc()).limit(10)
        ))
        evolver_mems = evolver.scalars().all()

        tefas_ctx = {"price": latest.unit_price, "total_value": latest.total_value or 0, "participants": latest.participant_count or 0}
        ai = await _analyze(pdf_text, fund_code, tefas_ctx, history, evolver_mems)

        # Ay bazlı en yakın kaydı bul
        month_key = ai.get("monthKey", latest.month_key)
        target = (await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code, FundRecord.month_key == month_key)
            .order_by(desc(FundRecord.date_key)).limit(1)
        )).scalar_one_or_none() or latest

        target.has_pdf_analysis = 1
        target.monthly_return = ai.get("monthlyReturn")
        target.yearly_return = ai.get("yearlyReturn")
        # En son kaydı da güncelle (infografik için)
        if latest and latest != target:
            latest.monthly_return = ai.get("monthlyReturn")
            latest.yearly_return = ai.get("yearlyReturn")
            latest.risk_score = ai.get("riskScore")
            latest.stopaj_rate = ai.get("stopajRate")
            latest.valor = ai.get("valor")
            latest.fund_type = ai.get("fundType")
            latest.ai_insights = json.dumps(ai.get("aiInsights", []), ensure_ascii=False)
            latest.dexter_recommendations = json.dumps(ai.get("dexterRecommendations", []), ensure_ascii=False)
            latest.twitter_summary = ai.get("twitterSummary", "")
            latest.has_pdf_analysis = 1
        # target == latest olsa bile AI alanlarını güncelle
        target.ai_insights = json.dumps(ai.get("aiInsights", []), ensure_ascii=False)
        target.dexter_recommendations = json.dumps(ai.get("dexterRecommendations", []), ensure_ascii=False)
        target.twitter_summary = ai.get("twitterSummary", "")
        target.avg_maturity = ai.get("avgMaturity")
        target.monthly_turnover = ai.get("monthlyTurnover")
        target.top_holdings = json.dumps(ai.get("topHoldings", []), ensure_ascii=False)
        target.expenses = json.dumps(ai.get("expenses", {}), ensure_ascii=False)
        target.risk_score = ai.get("riskScore")
        target.stopaj_rate = ai.get("stopajRate")
        target.valor = ai.get("valor")
        target.fund_type = ai.get("fundType")
        target.ai_insights = json.dumps(ai.get("aiInsights", []), ensure_ascii=False)
        target.dexter_recommendations = json.dumps(ai.get("dexterRecommendations", []), ensure_ascii=False)
        target.twitter_summary = ai.get("twitterSummary", "")
        target.raw_pdf_text = pdf_text[:5000]
        if ai.get("portfolioItems"):
            target.portfolio_items = json.dumps(ai["portfolioItems"], ensure_ascii=False)
        await session.commit()

    return {"success": True, "fundCode": fund_code, "month": ai.get("month"), "monthKey": month_key}


@app.on_event("startup")
async def startup_event():
    async def nightly_refresh():
        print("🔄 Gece otomatik refresh başladı...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(FundRecord.fund_code).distinct())
            codes = [r[0] for r in result.fetchall()]
        for code in codes:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    r = await client.post(f"http://localhost:9009/api/funds/{code}/refresh", timeout=60)
                print(f"  ✅ {code} güncellendi")
            except Exception as e:
                print(f"  ❌ {code} hata: {e}")
        print(f"🔄 Tamamlandı. {len(codes)} fon güncellendi.")

    scheduler.add_job(nightly_refresh, CronTrigger(hour=3, minute=0), id="nightly_refresh", replace_existing=True)
    scheduler.start()
    print("⏰ Scheduler başlatıldı (her gece 03:00)")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

@app.post("/api/funds/{fund_code}/publish")
async def publish_fund(fund_code: str, published: bool = True):
    fund_code = fund_code.upper()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code)
            .order_by(FundRecord.date_key.desc()).limit(1))
        rec = result.scalar_one_or_none()
        if not rec:
            raise HTTPException(404, "Fon bulunamadı")
        rec.published = 1 if published else 0
        await session.commit()
    return {"ok": True, "fund_code": fund_code, "published": published}

@app.get("/api/public/funds")
async def get_public_funds():
    """fonar.com.tr için public JSON endpoint"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FundRecord).where(FundRecord.published == 1)
            .order_by(FundRecord.fund_code, FundRecord.date_key.desc()))
        rows = result.scalars().all()
        seen = set()
        funds = []
        for r in rows:
            if r.fund_code in seen:
                continue
            seen.add(r.fund_code)
            funds.append({
                "code": r.fund_code,
                "name": r.fund_name,
                "latestDate": r.date_key,
                "unitPrice": r.unit_price,
                "totalValue": r.total_value,
                "participantCount": r.participant_count,
                "monthlyReturn": r.monthly_return,
                "yearlyReturn": r.yearly_return,
                "riskScore": r.risk_score,
                "fundType": r.fund_type,
                "stopajRate": r.stopaj_rate,
                "valor": r.valor,
                "aiInsights": json.loads(r.ai_insights) if r.ai_insights else [],
                "dexterRecommendations": json.loads(r.dexter_recommendations) if r.dexter_recommendations else [],
                "twitterSummary": r.twitter_summary,
                "portfolioItems": json.loads(r.portfolio_items) if r.portfolio_items else [],
            })
    return funds

@app.get("/api/funds")
async def get_funds():
    async with AsyncSessionLocal() as session:
        # Her fon için en son kaydı çek
        all_records = (await session.execute(
            select(FundRecord).order_by(FundRecord.fund_code, desc(FundRecord.date_key))
        )).scalars().all()
    seen = set()
    funds = []
    for r in all_records:
        if r.fund_code in seen:
            continue
        seen.add(r.fund_code)
        funds.append({
            "code": r.fund_code, "name": r.fund_name,
            "latestDate": r.date_key, "unitPrice": r.unit_price,
            "totalValue": r.total_value, "participantCount": r.participant_count,
            "monthlyReturn": r.monthly_return, "yearlyReturn": r.yearly_return,
            "riskScore": r.risk_score, "fundType": r.fund_type,
            "hasPdfAnalysis": bool(r.has_pdf_analysis),
            "portfolioItems": json.loads(r.portfolio_items or "[]"),
        })
    return funds


@app.get("/api/funds/{fund_code}")
async def get_fund_detail(fund_code: str):
    fund_code = fund_code.upper()
    async with AsyncSessionLocal() as session:
        records = (await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code).order_by(desc(FundRecord.date_key))
        )).scalars().all()
    if not records:
        raise HTTPException(404, "Fon bulunamadı")
    r = records[0]
    return {
        "code": fund_code, "name": r.fund_name,
        "latestDate": r.date_key, "unitPrice": r.unit_price,
        "totalValue": r.total_value, "participantCount": r.participant_count,
        "shareCount": r.share_count,
        "monthlyReturn": r.monthly_return, "yearlyReturn": r.yearly_return,
        "avgMaturity": r.avg_maturity, "monthlyTurnover": r.monthly_turnover,
        "riskScore": r.risk_score, "stopajRate": r.stopaj_rate,
        "valor": r.valor, "fundType": r.fund_type,
        "hasPdfAnalysis": bool(r.has_pdf_analysis),
        "portfolioItems": json.loads(r.portfolio_items or "[]"),
        "topHoldings": json.loads(r.top_holdings or "[]"),
        "expenses": json.loads(r.expenses or "{}"),
        "aiInsights": json.loads(r.ai_insights or "[]"),
        "dexterRecommendations": json.loads(r.dexter_recommendations or "[]"),
        "twitterSummary": r.twitter_summary,
        "totalDays": len(records),
        "priceHistory": [
            {"date": rec.date_key, "price": rec.unit_price,
             "totalValue": rec.total_value, "participantCount": rec.participant_count}
            for rec in reversed(records)
        ],
        "pdfAnalyses": [
            {"dateKey": rec.date_key, "monthKey": rec.month_key,
             "monthlyReturn": rec.monthly_return, "yearlyReturn": rec.yearly_return,
             "aiInsights": json.loads(rec.ai_insights or "[]"),
             "dexterRecommendations": json.loads(rec.dexter_recommendations or "[]"),
             "twitterSummary": rec.twitter_summary}
            for rec in records if rec.has_pdf_analysis
        ][:6],
    }


@app.delete("/api/funds/{fund_code}")
async def delete_fund(fund_code: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(FundRecord).where(FundRecord.fund_code == fund_code.upper()))
        await session.execute(delete(EvolverMemory).where(EvolverMemory.fund_code == fund_code.upper()))
        await session.commit()
    return {"success": True}


@app.get("/api/evolver/{fund_code}")
async def get_evolver(fund_code: str):
    async with AsyncSessionLocal() as session:
        mems = (await session.execute(
            select(EvolverMemory).where(EvolverMemory.fund_code == fund_code.upper())
            .order_by(EvolverMemory.confidence.desc())
        )).scalars().all()
    return [{"type": m.memory_type, "content": m.content, "confidence": round(m.confidence, 2),
             "occurrenceCount": m.occurrence_count, "lastSeen": m.last_seen.isoformat()} for m in mems]


@app.post("/api/evolver/{fund_code}/manual-price")
async def learn_manual_price(fund_code: str, payload: dict = Body(...)):
    code = fund_code.upper()
    chg = payload.get("changePct", 0)
    month = payload.get("pdfMonth", "")
    async with AsyncSessionLocal() as session:
        for mtype, content, bump in [
            ("price_update", json.dumps(payload, ensure_ascii=False), 0.08),
            ("price_insight", f"{month} raporundan bu yana {'artış' if chg > 0 else 'düşüş'}: %{chg:+.2f}", 0.1),
        ]:
            ex = (await session.execute(select(EvolverMemory).where(
                EvolverMemory.fund_code == code, EvolverMemory.memory_type == mtype))).scalar_one_or_none()
            if ex:
                ex.content = content; ex.occurrence_count += 1
                ex.confidence = min(0.99, ex.confidence + bump); ex.last_seen = datetime.utcnow()
            else:
                session.add(EvolverMemory(fund_code=code, memory_type=mtype, content=content, confidence=0.5 + bump))
        await session.commit()
    return {"success": True, "insight": f"{month} raporundan bu yana: %{chg:+.2f}"}


@app.get("/api/benchmarks")
async def get_benchmarks():
    cached = _cache.get("benchmarks")
    if cached and (datetime.now() - cached["fetched_at"]).seconds < 3600:
        return {k: v for k, v in cached.items() if k != "fetched_at"}
    try:
        import yfinance as yf
        end = datetime.now()
        tickers = {"bist100": ("XU100.IS", "BİST 100"), "gold": ("GC=F", "Altın"), "usdtry": ("TRY=X", "Dolar/TL")}
        results = {}
        for key, (sym, name) in tickers.items():
            try:
                loop = asyncio.get_running_loop()
                def _f(s=sym):
                    import warnings; warnings.filterwarnings("ignore")
                    t = yf.Ticker(s)
                    def p(d):
                        h = t.history(start=end-timedelta(days=d+5), end=end)
                        return round(((h.Close.iloc[-1]-h.Close.iloc[0])/h.Close.iloc[0])*100,2) if len(h)>=2 else None
                    h = t.history(start=end-timedelta(days=35), end=end)
                    return {"name": name, "current": round(float(h.Close.iloc[-1]),4) if not h.empty else None,
                            "1m": p(30), "3m": p(90), "6m": p(180), "1y": p(365)}
                results[key] = await loop.run_in_executor(None, _f)
            except Exception as e:
                results[key] = {"name": name, "error": str(e)}
        results["fetched_at"] = datetime.now()
        _cache["benchmarks"] = results
        return {k: v for k, v in results.items() if k != "fetched_at"}
    except ImportError:
        raise HTTPException(500, "yfinance kurulu değil")



@app.get("/api/debug-tefas")
async def debug_tefas():
    import subprocess
    fund_code = "TLY"
    script = f"""
import urllib.request, urllib.parse, json, sys
url = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
data = urllib.parse.urlencode({{"fontip":"YAT","fonkod":"{fund_code}","bastarih":"01.02.2026","bittarih":"09.03.2026"}}).encode()
req = urllib.request.Request(url, data=data, method="POST")
with urllib.request.urlopen(req, timeout=15) as r:
    raw = r.read().decode("utf-8")
    sys.stdout.write(raw)
    sys.stdout.flush()
"""
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: subprocess.run(
        ["python3", "-c", script], capture_output=True, text=True, timeout=30, env=os.environ.copy()
    ))
    return {
        "stdout_len": len(result.stdout),
        "stderr": result.stderr[:200],
        "returncode": result.returncode,
        "preview": result.stdout[:100] if result.stdout else "BOŞ"
    }

@app.get("/api/stats")
async def get_stats():
    async with AsyncSessionLocal() as session:
        records = (await session.execute(select(FundRecord))).scalars().all()
        mems = (await session.execute(select(EvolverMemory))).scalars().all()
    codes = list(set(r.fund_code for r in records))
    return {"totalFunds": len(codes), "totalRecords": len(records),
            "pdfAnalyses": sum(1 for r in records if r.has_pdf_analysis),
            "evolverMemories": len(mems), "funds": codes}


# ─── STATIC ────────────────────────────────────────────────────────────────────
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(str(FRONTEND_DIST / "index.html"))
