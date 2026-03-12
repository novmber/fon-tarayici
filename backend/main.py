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

    async def nightly_refresh():
        print("🔄 11:30 otomatik güncelleme başladı...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(FundRecord.fund_code).distinct())
            codes = [r[0] for r in result.fetchall()]
        import asyncio as _asyncio
        for code in codes:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    # Refresh öncesi son fiyatı al
                    detail_before = await client.get(f"http://localhost:9009/api/funds/{code}", timeout=30)
                    price_before = detail_before.json().get("unitPrice") if detail_before.status_code == 200 else None

                    refresh_res = await client.post(f"http://localhost:9009/api/funds/{code}/refresh", timeout=60)
                    refresh_data = refresh_res.json() if refresh_res.status_code == 200 else {}
                    new_rows = refresh_data.get("newRows", 0)

                    # Refresh sonrası fiyatı al
                    detail_after = await client.get(f"http://localhost:9009/api/funds/{code}", timeout=30)
                    price_after = detail_after.json().get("unitPrice") if detail_after.status_code == 200 else None

                    if new_rows == 0 and price_before == price_after:
                        print(f"  ⏭️ {code} fiyat değişmedi, analiz atlandı")
                        continue

                    print(f"  ✅ {code} fiyat güncellendi ({new_rows} yeni kayıt)")
                    await _asyncio.sleep(3)
                    await client.post(f"http://localhost:9009/api/funds/{code}/analyze-tefas", timeout=120)
                    print(f"  🤖 {code} analiz tamamlandı")
                    await _asyncio.sleep(5)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    import re
                    wait_match = re.search(r'try again in (\d+)m', err_str)
                    wait_min = int(wait_match.group(1)) + 1 if wait_match else 12
                    print(f"  ⏳ Rate limit — {wait_min} dakika bekleniyor...")
                    await _asyncio.sleep(wait_min * 60)
                    try:
                        async with httpx.AsyncClient() as client2:
                            await client2.post(f"http://localhost:9009/api/funds/{code}/analyze-tefas", timeout=120)
                            print(f"  🤖 {code} analiz tamamlandı (retry)")
                    except Exception as e2:
                        print(f"  ❌ {code} retry hata: {e2}")
                else:
                    print(f"  ❌ {code} hata: {e}")
        print(f"✅ Tamamlandı. {len(codes)} fon güncellendi ve analiz edildi.")
        import subprocess
        subprocess.Popen(["/bin/bash", "/root/FONAR/export-public.sh"])
        print("📤 Fonar export başlatıldı")

    scheduler.add_job(nightly_refresh, CronTrigger(hour=11, minute=30), id="nightly_refresh", replace_existing=True)
    scheduler.start()
    print("⏰ Scheduler başlatıldı (her gün 11:30)")


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



async def _tefas_fund_info(fund_code: str) -> dict:
    """BindFundInfo: risk skoru, stopaj, valor, fon tipi, yönetici"""
    today = datetime.now().strftime("%d.%m.%Y")
    script = str(Path(__file__).parent / "tefas_fetch.py")
    try:
        result = await asyncio.to_thread(subprocess.run,
            ["python3", script, "BindFundInfo", fund_code, today, today],
            capture_output=True, text=True, timeout=30)
        if not result.stdout or result.stdout.strip().startswith("<"):
            return {}
        data = json.loads(result.stdout).get("data", [])
        return data[0] if data else {}
    except Exception as e:
        print(f"⚠️  TEFAS fund_info ({fund_code}): {e}")
        return {}

async def _tefas_top_holdings(fund_code: str) -> list:
    """BindHistoryAllocationTop: top 10 portföy varlığı"""
    today = datetime.now().strftime("%d.%m.%Y")
    start = (datetime.now() - timedelta(days=7)).strftime("%d.%m.%Y")
    script = str(Path(__file__).parent / "tefas_fetch.py")
    try:
        result = await asyncio.to_thread(subprocess.run,
            ["python3", script, "BindHistoryAllocationTop", fund_code, start, today],
            capture_output=True, text=True, timeout=30)
        if not result.stdout or result.stdout.strip().startswith("<"):
            return []
        rows = json.loads(result.stdout).get("data", [])
        if not rows:
            return []
        latest = rows[-1]
        holdings = []
        for i in range(1, 11):
            name = latest.get(f"VARLIKADI{i}", "")
            weight = latest.get(f"YUZDE{i}", 0)
            if name and float(weight or 0) > 0:
                holdings.append({"name": name, "weight": round(float(weight), 2)})
        return holdings
    except Exception as e:
        print(f"⚠️  TEFAS top_holdings ({fund_code}): {e}")
        return []

# ─── EVOLVER ───────────────────────────────────────────────────────────────────

async def _verify_predictions(session: AsyncSession, fund_code: str, current_price: float, current_date: str):
    """Geçmiş Dexter tahminlerini doğrula ve doğruluk skorunu güncelle"""
    preds = (await session.execute(
        select(EvolverMemory).where(
            EvolverMemory.fund_code == fund_code,
            EvolverMemory.memory_type == "dexter_prediction"
        ).order_by(EvolverMemory.snapshot_date)
    )).scalars().all()

    accuracy_results = []
    for pred_rec in preds:
        try:
            pred = json.loads(pred_rec.content)
        except:
            continue
        pred_date = pred.get("date", "")
        pred_price = pred.get("price_at_prediction", 0)
        direction = pred.get("direction", "neutral")
        if not pred_price or not pred_date:
            continue
        # Kaç gün geçti
        try:
            from datetime import date as _date
            d0 = _date.fromisoformat(pred_date)
            d1 = _date.fromisoformat(current_date)
            days_passed = (d1 - d0).days
        except:
            continue
        if days_passed < 7:
            continue
        # Fiyat değişimi
        price_change_pct = round((current_price - pred_price) / pred_price * 100, 2) if pred_price else 0
        updated = False
        # 7 günlük doğrulama
        if days_passed >= 7 and pred.get("verified_7d") is None:
            actual = "bullish" if price_change_pct > 1 else "bearish" if price_change_pct < -1 else "neutral"
            pred["verified_7d"] = True
            pred["result_7d"] = {"days": 7, "price_change": price_change_pct, "actual": actual, "correct": actual == direction}
            updated = True
        # 14 günlük doğrulama
        if days_passed >= 14 and pred.get("verified_14d") is None:
            actual = "bullish" if price_change_pct > 1.5 else "bearish" if price_change_pct < -1.5 else "neutral"
            pred["verified_14d"] = True
            pred["result_14d"] = {"days": 14, "price_change": price_change_pct, "actual": actual, "correct": actual == direction}
            updated = True
        # 30 günlük doğrulama
        if days_passed >= 30 and pred.get("verified_30d") is None:
            actual = "bullish" if price_change_pct > 3 else "bearish" if price_change_pct < -3 else "neutral"
            pred["verified_30d"] = True
            pred["result_30d"] = {"days": 30, "price_change": price_change_pct, "actual": actual, "correct": actual == direction}
            updated = True
        if updated:
            pred_rec.content = json.dumps(pred, ensure_ascii=False)
            pred_rec.last_seen = datetime.utcnow()
        # Doğruluk istatistiği topla
        for key in ["result_7d", "result_14d", "result_30d"]:
            r = pred.get(key)
            if r:
                accuracy_results.append(r.get("correct", False))

    # Genel doğruluk skorunu kaydet
    if accuracy_results:
        accuracy_pct = round(sum(1 for r in accuracy_results if r) / len(accuracy_results) * 100, 1)
        total = len(accuracy_results)
        acc_ex = await session.execute(select(EvolverMemory).where(
            EvolverMemory.fund_code == fund_code,
            EvolverMemory.memory_type == "signal_accuracy"
        ))
        acc_rec = acc_ex.scalar_one_or_none()
        acc_content = json.dumps({
            "accuracy_pct": accuracy_pct,
            "total_predictions": total,
            "correct": sum(1 for r in accuracy_results if r),
            "last_updated": current_date
        }, ensure_ascii=False)
        if acc_rec:
            acc_rec.content = acc_content
            acc_rec.last_seen = datetime.utcnow()
        else:
            session.add(EvolverMemory(
                fund_code=fund_code,
                memory_type="signal_accuracy",
                content=acc_content,
                confidence=0.7,
                snapshot_date=datetime.utcnow().date(),
            ))
    await session.commit()


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

    # Kazanç/Risk Skoru (risksiz oran %45 → günlük ~0.123%)
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
        "kazanc_risk_skoru": round(sharpe, 2),
        "positive_days_pct": pos_ratio,
        "momentum_30d": momentum,
        "best_month": {"month": best_month[0], "return": round(best_month[1], 2)} if best_month else None,
        "worst_month": {"month": worst_month[0], "return": round(worst_month[1], 2)} if worst_month else None,
        "sample_count": len(prices),
        "latest_price": round(prices[-1], 6),
        "total_return": round((prices[-1] - prices[0]) / prices[0] * 100, 2),
    }, ensure_ascii=False)

    today = datetime.utcnow().date()
    today_str = today.strftime("%Y-%m-%d")

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
        sharpes = [d.get("kazanc_risk_skoru") for d in snapdata if d.get("kazanc_risk_skoru") is not None]
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
        # Sharpe bazlı sinyal
        sharpe = curr.get("kazanc_risk_skoru", 0) or 0
        if sharpe >= 1.0:
            signals.append({"type": "pozitif", "msg": f"Faiz üstü kazanç skoru {sharpe:.2f} — enflasyon ve faize göre iyi getiri sağlıyor"})
        elif sharpe < 0:
            signals.append({"type": "negatif", "msg": f"Faiz üstü kazanç skoru negatif — bu fon banka faizinin bile altında getiri sağlıyor"})
        else:
            signals.append({"type": "uyarı", "msg": f"Faiz üstü kazanç skoru {sharpe:.2f} — getiri orta düzeyde, faizi biraz geçiyor"})

        # Momentum sinyali
        mom = curr.get("momentum_30d", 0) or 0
        if mom > 5:
            signals.append({"type": "pozitif", "msg": f"Momentum +{mom:.1f}% — güçlü kısa vadeli ivme"})
        elif mom < -5:
            signals.append({"type": "negatif", "msg": f"Momentum {mom:.1f}% — zayıf kısa vadeli ivme"})

        # Volatilite sinyali
        vol = curr.get("annual_volatility", 0) or 0
        if vol > 80:
            signals.append({"type": "uyarı", "msg": f"Yıllık volatilite %{vol:.1f} — yüksek risk"})
        elif vol < 20:
            signals.append({"type": "pozitif", "msg": f"Yıllık volatilite %{vol:.1f} — düşük risk"})

        # Drawdown sinyali
        dd = curr.get("max_drawdown", 0) or 0
        if dd < -30:
            signals.append({"type": "negatif", "msg": f"Max drawdown %{dd:.1f} — tarihi kayıp yüksek"})
        elif dd > -10:
            signals.append({"type": "pozitif", "msg": f"Max drawdown %{dd:.1f} — kayıp kontrol altında"})

        # Pozitif gün
        pos_days = curr.get("positive_days_pct", 0) or 0
        if pos_days > 55:
            signals.append({"type": "pozitif", "msg": f"Pozitif gün oranı %{pos_days:.1f} — tutarlı getiri"})
        elif pos_days < 40:
            signals.append({"type": "uyarı", "msg": f"Pozitif gün oranı %{pos_days:.1f} — dalgalı seyir"})

        # Trend sinyalleri
        if sharpe_trend == "artıyor":
            signals.append({"type": "pozitif", "msg": "Kazanç kalitesi artıyor — son dönemde faiz üstü getiri güçleniyor"})
        if mom_trend == "güçleniyor":
            signals.append({"type": "pozitif", "msg": "Momentum güçleniyor — ivme artıyor"})
        if vol_trend == "artıyor":
            signals.append({"type": "uyarı", "msg": "Volatilite tırmanıyor — dikkatli olun"})
        if dd_trend == "iyileşiyor":
            signals.append({"type": "pozitif", "msg": "Drawdown iyileşiyor — toparlanma sinyali"})

        signal_content = json.dumps({
            "sharpe_trend": sharpe_trend,
            "momentum_trend": mom_trend,
            "volatility_trend": vol_trend,
            "drawdown_trend": dd_trend,
            "snapshot_count": len(all_snaps),
            "signals": signals,
            "last_kazanc_skoru": sharpes[-1] if sharpes else None,
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
    # ─── FON KARAKTERİ ───────────────────────────────────────────────────────
    if len(prices) >= 60:
        char = {}
        monthly_avgs = {}
        for ym, ps in monthly.items():
            if len(ps) >= 15:
                monthly_avgs[ym[-2:]] = round((ps[-1] - ps[0]) / ps[0] * 100, 2)
        if monthly_avgs:
            best_month_num = max(monthly_avgs, key=monthly_avgs.get)
            worst_month_num = min(monthly_avgs, key=monthly_avgs.get)
            month_names = {"01":"Ocak","02":"Şubat","03":"Mart","04":"Nisan","05":"Mayıs",
                          "06":"Haziran","07":"Temmuz","08":"Ağustos","09":"Eylül",
                          "10":"Ekim","11":"Kasım","12":"Aralık"}
            char["best_season"] = f"{month_names.get(best_month_num, best_month_num)}: ort. %{monthly_avgs[best_month_num]:+.1f}"
            char["worst_season"] = f"{month_names.get(worst_month_num, worst_month_num)}: ort. %{monthly_avgs[worst_month_num]:+.1f}"
        recovery_days = []
        in_dd = False
        dd_start = 0
        peak_p = prices[0]
        for i, p in enumerate(prices):
            if p >= peak_p:
                if in_dd:
                    recovery_days.append(i - dd_start)
                    in_dd = False
                peak_p = p
            elif (peak_p - p) / peak_p * 100 > 5 and not in_dd:
                in_dd = True
                dd_start = i
        avg_recovery = round(sum(recovery_days) / len(recovery_days)) if recovery_days else None
        char["avg_recovery_days"] = avg_recovery
        if avg_recovery:
            char["recovery_profile"] = ("hızlı toparlanıyor" if avg_recovery <= 10 else "orta hızda toparlanıyor" if avg_recovery <= 30 else "yavaş toparlanıyor") + f" (ort. {avg_recovery} gün)"
        consistency = 0
        if pos_ratio >= 55: consistency += 2
        elif pos_ratio >= 50: consistency += 1
        if max_dd < 10: consistency += 2
        elif max_dd < 20: consistency += 1
        if ann_vol < 20: consistency += 1
        char["consistency_score"] = consistency
        char["consistency_label"] = "yüksek" if consistency >= 4 else "orta" if consistency >= 2 else "düşük"
        if len(prices) >= 90:
            m1 = round((prices[-1] - prices[-22]) / prices[-22] * 100, 2)
            m2 = round((prices[-22] - prices[-44]) / prices[-44] * 100, 2) if len(prices) >= 44 else None
            m3 = round((prices[-44] - prices[-66]) / prices[-66] * 100, 2) if len(prices) >= 66 else None
            char["monthly_momentum"] = [m for m in [m3, m2, m1] if m is not None]
            if m2 is not None:
                char["momentum_pattern"] = "ivme kazanıyor" if m1 > m2 else "ivme kaybediyor" if m1 < m2 * 0.5 else "ivme sabit"
        total_ret = round((prices[-1] - prices[0]) / prices[0] * 100, 2)
        vol_label = "yüksek dalgalanmalı" if ann_vol > 40 else "düşük dalgalanmalı" if ann_vol < 15 else "orta dalgalanmalı"
        summary_parts = [f"{len(prices)} günde %{total_ret:+.1f} toplam getiri", vol_label]
        if avg_recovery: summary_parts.append(f"düşüşten ort. {avg_recovery} günde çıkıyor")
        if char.get("best_season"): summary_parts.append(f"en güçlü dönem {char['best_season']}")
        char["summary"] = ", ".join(summary_parts)
        char_content = json.dumps(char, ensure_ascii=False)
        char_ex = await session.execute(select(EvolverMemory).where(
            EvolverMemory.fund_code == fund_code,
            EvolverMemory.memory_type == "fund_character"))
        char_rec = char_ex.scalar_one_or_none()
        if char_rec:
            char_rec.content = char_content
            char_rec.occurrence_count += 1
            char_rec.confidence = min(0.99, char_rec.confidence + 0.02)
            char_rec.last_seen = datetime.utcnow()
        else:
            session.add(EvolverMemory(
                fund_code=fund_code,
                memory_type="fund_character",
                content=char_content,
                confidence=0.6,
                snapshot_date=today,
            ))

    # Geçmiş tahminleri doğrula
    if prices:
        today_str = datetime.utcnow().date().strftime("%Y-%m-%d")
        await _verify_predictions(session, fund_code, prices[-1], today_str)

    await session.commit()


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



async def _analyze_tefas(fund_code: str, fund_info: dict, evolver: dict, history: list, top_holdings: list) -> dict:
    """TEFAS + Evolver verisiyle Groq/Llama analizi"""
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "GROQ_API_KEY bulunamadı")

    prices = [r["unit_price"] for r in history if r.get("unit_price", 0) > 0]
    total_return = round((prices[-1] - prices[0]) / prices[0] * 100, 2) if len(prices) >= 2 else 0
    recent_prices = prices[-30:] if len(prices) >= 30 else prices
    monthly_return = round((recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100, 2) if len(recent_prices) >= 2 else 0

    # 6 aylık ortalama aylık getiri
    monthly_returns = []
    if len(prices) >= 60:
        for i in range(6):
            end_i = len(prices) - i * 30
            start_i = end_i - 30
            if start_i >= 0:
                r = round((prices[end_i-1] - prices[start_i]) / prices[start_i] * 100, 2)
                monthly_returns.append(r)
    avg_6m_monthly = round(sum(monthly_returns) / len(monthly_returns), 2) if monthly_returns else None

    ev_signals = evolver.get("signals", [])
    ev_str = ""
    # fund_character verisini çek
    char_data = {}
    async with AsyncSessionLocal() as _cs:
        from sqlalchemy import select as _sel
        _cr = await _cs.execute(_sel(EvolverMemory).where(
            EvolverMemory.fund_code == fund_code,
            EvolverMemory.memory_type == "fund_character"))
        _crec = _cr.scalar_one_or_none()
        if _crec:
            try: char_data = json.loads(_crec.content)
            except: pass
    if evolver:
        char_summary = char_data.get("summary", "")
        char_recovery = char_data.get("recovery_profile", "")
        char_season = f"En iyi: {char_data.get('best_season','')} / En kötü: {char_data.get('worst_season','')}" if char_data.get("best_season") else ""
        char_momentum = char_data.get("momentum_pattern", "")
        char_consistency = char_data.get("consistency_label", "")
        # Doğruluk geçmişini çek
        acc_str = "henüz yeterli veri yok"
        async with AsyncSessionLocal() as _as:
            _ar = await _as.execute(_sel(EvolverMemory).where(
                EvolverMemory.fund_code == fund_code,
                EvolverMemory.memory_type == "signal_accuracy"))
            _arec = _ar.scalar_one_or_none()
            if _arec:
                try:
                    _ad = json.loads(_arec.content)
                    acc_str = f"%{_ad.get('accuracy_pct','?')} doğruluk ({_ad.get('total_predictions','?')} test) — {_ad.get('signal_note','')}"
                except: pass
        ev_str = f"""
DEXTER DOĞRULUK GEÇMİŞİ: {acc_str}
FON KARAKTERİ: {char_summary}
Toparlanma: {char_recovery} | Tutarlılık: {char_consistency} | Momentum: {char_momentum}
Mevsimsel: {char_season}
EVOLVER: FaizÜstüKazançSkoru={evolver.get("last_kazanc_skoru","?")} ({evolver.get("sharpe_trend","?")}), Momentum={evolver.get("last_momentum","?")}% ({evolver.get("momentum_trend","?")}), Drawdown trendi={evolver.get("drawdown_trend","?")}
Sinyaller: {", ".join([s["msg"] for s in ev_signals[:3]])}"""

    holdings_str = ""
    if top_holdings:
        holdings_str = "\nTOP VARLIKLAR: " + ", ".join([h["name"] + " %" + str(h["weight"]) for h in top_holdings[:5]])

    alloc_str = ""
    if fund_info.get("portfolioItems"):
        items = fund_info["portfolioItems"]
        alloc_str = "\nPORTFÖY DAĞILIMI: " + ", ".join([i["name"] + " %" + str(i["value"]) for i in items[:5]])

    months_tr = {1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",
                 7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık"}
    now = datetime.now()
    current_month_str = f"{months_tr[now.month]} {now.year}"

    prompt = f"""Sen bir Türk yatırım fonu analistisin.

FON VERİLERİ:
- Kod: {fund_code} | Ad: {fund_info.get("name", "")}
- Tür: {fund_info.get("fundType", "?")} | Risk: {fund_info.get("riskScore", "?")}/7
- Güncel Fiyat: {prices[-1] if prices else "?"} TL
- Portföy Büyüklüğü: {round(fund_info.get("totalValue", 0)/1e6, 1)}M TL
- Yatırımcı Sayısı: {int(fund_info.get("participantCount", 0)):,}
- Aylık Getiri: %{monthly_return}
- 6 Aylık Ort. Aylık Getiri: %{avg_6m_monthly if avg_6m_monthly is not None else "?"}
- Toplam Getiri ({len(prices)} gün): %{total_return}
- Stopaj: %{fund_info.get("stopajRate", 17.5)} | Valör: {fund_info.get("valor", "T+1/T+2")}
{holdings_str}{alloc_str}{ev_str}

KURALLAR:
- Türkçe yaz.
- Sadece yukarıdaki verileri kullan.
- Veri bulunmayan konuda yorum yapma.
- Her tespit en az bir sayısal veri içermelidir.
- Genel ifadeler kullanma (örn: güçlü performans, iyi getiri vb.)
- Her tespit "veri → sonuç" formatında olmalıdır.
- Fonun performansı, risk seviyesi ve yatırımcı davranışı hakkında somut analiz üret.
- Analiz TEFAS fon verilerine uygun olmalıdır.
- twitterSummary 280 karakteri geçmemeli, gerçek sayılar kullanılmalı.
- JSON dışında hiçbir çıktı üretme.
- aiInsights: Her biri veri-sonuç formatında, sayısal içeren 5 analitik tespit.
- dexterRecommendations: Teknik bilgisi olmayan bireysel yatırımcıya yönelik 3 somut aksiyon önerisi. Pasif ifadeler KESİNLİKLE YASAK. Her öneri bir koşul veya aksiyon içermeli. Teknik terim kullanma (Sharpe, volatilite, beta, kazanç skoru yasak). Günlük dil kullan. İyi örnek: Son ayda yüzde 7 düşen bu fon ortalamasının çok altında, yeni giriş yapmak yerine toparlanmayı bekle. İyi örnek: Paranın yüzde 68i dolar bazlı hisselerde, dolar yükselirse fon değer kazanır. Kötü örnek: Yatırımcılar riski dikkate almalıdır, BU TARZI YAZMA.
İyi örnek 3: Bu fon 1 yılda yüzde 104 kazandırdı ama bu ay sert düştü, varsa karının bir kısmını çek, tamamını tutma.
İyi örnek 4: Fon yüzde 17.5 stopaj kesiyor, kısa vadeli alım satım yaparsan bu vergiyi sık ödersin, uzun tut.
- aiInsights: Her biri "veri sonuc" formatinda, sayisal iceren 5 analitik tespit.
- dexterRecommendations: Teknik bilgisi olmayan bireysel yatirimciya yonelik 3 somut aksiyon onerisi. Pasif ifadeler YASAK. Her oneri bir kosul veya aksiyon icermeli. Teknik terim kullanma. Gunluk dil kullan. Iyi ornek: Son ayda yuzde 7 dusen bu fon ortalamasinin cok altinda, yeni giris yapmak yerine toparlanmayi bekle. Kotu ornek: Yatirimcilar riski dikkate almalidir BU TARZI YAZMA.

Örnek tespit: "Aylık getiri %{monthly_return} olup 6 aylık ortalama olan %{avg_6m_monthly}'in {'üzerindedir' if avg_6m_monthly and monthly_return > avg_6m_monthly else 'altındadır'}."

ÇIKTI (sadece JSON):
{{"aiInsights":["tespit1","tespit2","tespit3","tespit4","tespit5"],
  "dexterRecommendations":["öneri1","öneri2","öneri3"],
  "twitterSummary":"📊 {fund_code} | KISAAD\n━━━━━━━━━━━━━━\n🚀 Aylık: %{monthly_return} | Toplam ({len(prices)}g): %{total_return}\n💼 {round(fund_info.get("totalValue",0)/1e6,0):.0f}M TL | {int(fund_info.get("participantCount",0)):,} yatırımcı\n⚠️ Risk: {fund_info.get("riskScore","?")} /7\n\n🔍 Öne Çıkanlar:\n• veri bazlı tespit 1\n• veri bazlı tespit 2\n• veri bazlı tespit 3\n\n📅 {current_month_str} · TEFAS\n#YatırımFonu #TEFAS"}}"""

    client = Groq(api_key=api_key)
    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(None, lambda: client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Sen bir Türk yatırım fonu analistisin. Sadece JSON döndür, başka hiçbir şey yazma."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.3,
        response_format={"type": "json_object"},
    ))
    text = resp.choices[0].message.content.strip()
    ai = json.loads(text)

    # Tweet metnini Python'da oluştur — Groq'a bırakma
    fund_name_short = fund_info.get("name", fund_code)[:40]
    tv = fund_info.get("totalValue", 0) or 0
    tv_str = f"₺{tv/1e9:.2f}B" if tv >= 1e9 else f"₺{tv/1e6:.0f}M"
    pc = int(fund_info.get("participantCount", 0) or 0)
    risk = fund_info.get("riskScore", "?")
    risk_label = {"1":"Çok Düşük","2":"Düşük","3":"Orta-Düşük","4":"Orta","5":"Orta-Yüksek","6":"Yüksek","7":"Çok Yüksek"}.get(str(risk), "?")
    sharpe = evolver.get("last_sharpe", "?")
    # Evolver'dan sharpe al
    sharpe = "?"
    if evolver:
        sharpe = evolver.get("last_sharpe", "?")
    else:
        # price_pattern memory'den al
        pass
    # Öne çıkanlar: kısa ve veri bazlı, Python'da üret
    highlights = []
    # 1. En büyük portföy kalemi
    items = fund_info.get("portfolioItems", [])
    if items:
        top_item = max(items, key=lambda x: x.get("value", 0))
        highlights.append(f'{top_item["name"]} %{top_item["value"]:.1f} ile en büyük kalem')
    # 2. Sharpe yorumu
    if sharpe != "?" and sharpe is not None:
        try:
            s = float(sharpe)
            if s >= 2:
                highlights.append(f"Sharpe {s:.2f} — risk/getiri dengesi güçlü")
            elif s >= 1:
                highlights.append(f"Sharpe {s:.2f} — risk/getiri dengesi iyi")
            else:
                highlights.append(f"Sharpe {s:.2f} — orta düzey risk/getiri")
        except: pass
    # 3. Aylık vs 6 aylık karşılaştırma
    if avg_6m_monthly is not None:
        if monthly_return > avg_6m_monthly:
            highlights.append(f"Aylık %{monthly_return} → 6a ort. %{avg_6m_monthly}'nin üzerinde")
        else:
            highlights.append(f"Aylık %{monthly_return} → 6a ort. %{avg_6m_monthly}'nin altında")
    # Yedek: aiInsights'tan kısa al
    if len(highlights) < 3:
        for ins in ai.get("aiInsights", []):
            if len(highlights) >= 3: break
            short = ins[:55] + ("…" if len(ins) > 55 else "")
            highlights.append(short)
    bullet_str = "\n".join(["• " + h for h in highlights])
    monthly_sign = "+" if monthly_return >= 0 else ""
    total_sign = "+" if total_return >= 0 else ""
    twitter_summary = (
        "📊 " + fund_code + " | " + fund_name_short + "\n"
        "━━━━━━━━━━━━━━\n"
        "🚀 Aylık: " + monthly_sign + str(monthly_return) + "% | Toplam (" + str(len(prices)) + "g): " + total_sign + str(total_return) + "%\n"
        "💼 Portföy: " + tv_str + " | " + f"{pc:,}".replace(",", ".") + " yatırımcı\n"
        "⚠️ Risk: " + str(risk) + "/7 · " + risk_label + " · Sharpe: " + str(sharpe) + "\n"
        "\n🔍 Öne Çıkanlar:\n" + bullet_str + "\n"
        "\n📅 " + current_month_str + " · TEFAS\n"
        "#YatırımFonu #TEFAS #" + fund_code
    )
    ai["twitterSummary"] = twitter_summary
    return ai


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
    fund_info = await _tefas_fund_info(fund_code)
    top_holdings = await _tefas_top_holdings(fund_code)
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
                risk_score=int(fund_info.get("RISKDEGERI", 0) or 0) or None,
                stopaj_rate=float(fund_info.get("STOPAJORAN", 0) or 0) or None,
                valor=fund_info.get("VALÖR") or fund_info.get("VALOR"),
                fund_type=fund_info.get("FONTUR"),
                top_holdings=json.dumps(top_holdings, ensure_ascii=False),
            ))
            new_count += 1
        if fund_info:
            from sqlalchemy import update
            await session.execute(update(FundRecord).where(FundRecord.fund_code == fund_code).values(
                risk_score=int(fund_info.get("RISKDEGERI", 0) or 0) or None,
                stopaj_rate=float(fund_info.get("STOPAJORAN", 0) or 0) or None,
                valor=fund_info.get("VALÖR") or fund_info.get("VALOR"),
                fund_type=fund_info.get("FONTUR"),
                top_holdings=json.dumps(top_holdings, ensure_ascii=False),
            ))

        await session.commit()
        # Tüm geçmiş kayıtları çek — evolver için
        from sqlalchemy import text as sa_text
        all_records = await session.execute(
            sa_text("SELECT date_key, unit_price, total_value FROM fund_records WHERE fund_code=:code ORDER BY date_key"),
            {"code": fund_code})
        all_rows_full = [{"date_key": r[0], "unit_price": r[1], "total_value": r[2]} for r in all_records.fetchall()]
        await _update_evolver(session, fund_code, all_rows_full)
        await session.commit()

    # Otomatik analiz ve yayınla
    try:
        ai = await _analyze_tefas(fund_code, {
            "name": fund_name,
            "fundType": fund_info.get("FONTUR"),
            "riskScore": int(fund_info.get("RISKDEGERI", 0) or 0) or None,
            "totalValue": float(rows[0].get("PORTFOYBUYUKLUK", 0)) if rows else 0,
            "participantCount": float(rows[0].get("KISISAYISI", 0)) if rows else 0,
        }, {}, all_rows_full, top_holdings)
        async with AsyncSessionLocal() as session2:
            from sqlalchemy import update as sa_update
            await session2.execute(sa_update(FundRecord).where(FundRecord.fund_code == fund_code).values(
                ai_insights=json.dumps(ai.get("aiInsights", []), ensure_ascii=False),
                dexter_recommendations=json.dumps(ai.get("dexterRecommendations", []), ensure_ascii=False),
                twitter_summary=ai.get("twitterSummary", ""),
                published=1,
            ))
            await session2.commit()
        print(f"✅ {fund_code} otomatik analiz + yayınlandı")
        import subprocess, threading
        def delayed_export():
            import time, subprocess
            time.sleep(5)
            result = subprocess.run(["/bin/bash", "/root/FONAR/export-public.sh"], capture_output=True, text=True)
            print(f"📤 Export tamamlandı: {result.stdout[-200:] if result.stdout else ''}")
            if result.returncode != 0:
                print(f"❌ Export hata: {result.stderr[-200:] if result.stderr else ''}")
        import threading
        threading.Thread(target=delayed_export, daemon=True).start()
        print(f"📤 {fund_code} export başlatıldı (5sn sonra)")
    except Exception as e:
        print(f"⚠️ {fund_code} otomatik analiz hatası: {e}")
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
    fund_info = await _tefas_fund_info(fund_code)
    top_holdings = await _tefas_top_holdings(fund_code)
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
                risk_score=int(fund_info.get("RISKDEGERI", 0) or 0) or None,
                stopaj_rate=float(fund_info.get("STOPAJORAN", 0) or 0) or None,
                valor=fund_info.get("VALÖR") or fund_info.get("VALOR"),
                fund_type=fund_info.get("FONTUR"),
                top_holdings=json.dumps(top_holdings, ensure_ascii=False),
            ))
            new_count += 1
        # Fiyat geçmişinden aylık/yıllık getiri hesapla
        all_prices = (await session.execute(
            select(FundRecord.date_key, FundRecord.unit_price)
            .where(FundRecord.fund_code == fund_code, FundRecord.unit_price > 0)
            .order_by(FundRecord.date_key)
        )).fetchall()
        if len(all_prices) >= 2:
            latest_price = all_prices[-1][1]
            price_30d = all_prices[max(0, len(all_prices)-31)][1]
            price_365d = all_prices[max(0, len(all_prices)-252)][1]
            calc_monthly = round((latest_price - price_30d) / price_30d * 100, 2) if price_30d else None
            calc_yearly = round((latest_price - price_365d) / price_365d * 100, 2) if price_365d else None
        else:
            calc_monthly = calc_yearly = None
        from sqlalchemy import update
        # Mevcut en iyi değerleri bul (eski kayıtlardan)
        existing_meta = (await session.execute(
            select(FundRecord).where(
                FundRecord.fund_code == fund_code,
                FundRecord.risk_score != None
            ).order_by(desc(FundRecord.date_key)).limit(1)
        )).scalar_one_or_none()
        update_vals = {}
        if fund_info:
            update_vals = {
                "risk_score": int(fund_info.get("RISKDEGERI", 0) or 0) or None,
                "stopaj_rate": float(fund_info.get("STOPAJORAN", 0) or 0) or None,
                "valor": fund_info.get("VALÖR") or fund_info.get("VALOR"),
                "fund_type": fund_info.get("FONTUR"),
            }
        elif existing_meta:
            update_vals = {
                "risk_score": existing_meta.risk_score,
                "stopaj_rate": existing_meta.stopaj_rate,
                "valor": existing_meta.valor,
                "fund_type": existing_meta.fund_type,
            }
        if top_holdings:
            update_vals["top_holdings"] = json.dumps(top_holdings, ensure_ascii=False)
        elif existing_meta and existing_meta.top_holdings:
            update_vals["top_holdings"] = existing_meta.top_holdings
        if calc_monthly is not None:
            update_vals["monthly_return"] = calc_monthly
        if calc_yearly is not None:
            update_vals["yearly_return"] = calc_yearly
        if update_vals:
            await session.execute(update(FundRecord).where(FundRecord.fund_code == fund_code).values(**update_vals))
        await session.commit()
        all_rows_full = (await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code).order_by(FundRecord.date_key)
        )).scalars().all()
        all_rows_dict = [{"unit_price": r.unit_price, "date_key": r.date_key} for r in all_rows_full]
        await _update_evolver(session, fund_code, all_rows_dict)
    return {"success": True, "fundCode": fund_code, "newRows": new_count}



@app.post("/api/funds/{fund_code}/analyze-tefas")
async def analyze_tefas(fund_code: str):
    """PDF olmadan TEFAS + Evolver verisiyle Claude analizi"""
    fund_code = fund_code.upper()
    async with AsyncSessionLocal() as session:
        # En son kayıt
        latest = (await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code)
            .order_by(desc(FundRecord.date_key)).limit(1)
        )).scalar_one_or_none()
        if not latest:
            raise HTTPException(404, f"{fund_code} bulunamadı")

        # Fiyat geçmişi
        history_records = (await session.execute(
            select(FundRecord).where(FundRecord.fund_code == fund_code)
            .order_by(FundRecord.date_key)
        )).scalars().all()
        history = [{"date_key": r.date_key, "unit_price": r.unit_price, "total_value": r.total_value}
                   for r in history_records]

        # Evolver sinyali
        evolver_rec = (await session.execute(
            select(EvolverMemory).where(
                EvolverMemory.fund_code == fund_code,
                EvolverMemory.memory_type == "signal"
            )
        )).scalar_one_or_none()
        evolver = json.loads(evolver_rec.content) if evolver_rec else {}

        # signal yoksa price_pattern'den sharpe al
        if not evolver:
            pattern_rec = (await session.execute(
                select(EvolverMemory).where(
                    EvolverMemory.fund_code == fund_code,
                    EvolverMemory.memory_type == "price_pattern"
                ).order_by(EvolverMemory.last_seen.desc()).limit(1)
            )).scalar_one_or_none()
            if pattern_rec:
                p = json.loads(pattern_rec.content)
                evolver = {
                    "last_sharpe": p.get("sharpe_ratio"),
                    "last_momentum": p.get("momentum_30d"),
                    "last_vol": p.get("annual_volatility"),
                    "sharpe_trend": "?", "momentum_trend": "?",
                    "volatility_trend": "?", "drawdown_trend": "?",
                    "signals": []
                }

        # Fon bilgileri
        fund_info = {
            "name": latest.fund_name,
            "fundType": latest.fund_type,
            "riskScore": latest.risk_score,
            "totalValue": latest.total_value,
            "participantCount": latest.participant_count,
            "stopajRate": latest.stopaj_rate,
            "valor": latest.valor,
            "portfolioItems": json.loads(latest.portfolio_items or "[]"),
        }
        top_holdings = json.loads(latest.top_holdings or "[]")

        # Claude analizi
        ai = await _analyze_tefas(fund_code, fund_info, evolver, history, top_holdings)

        # Tüm kayıtlara yaz
        from sqlalchemy import update
        await session.execute(update(FundRecord).where(FundRecord.fund_code == fund_code).values(
            ai_insights=json.dumps(ai.get("aiInsights", []), ensure_ascii=False),
            dexter_recommendations=json.dumps(ai.get("dexterRecommendations", []), ensure_ascii=False),
            twitter_summary=ai.get("twitterSummary", ""),
            has_pdf_analysis=1,
        ))
        await session.commit()

        # ── Dexter tahminini kaydet (feedback loop) ──────────────────────
        current_price = history[-1]["unit_price"] if history else None
        if current_price and ai.get("dexterRecommendations"):
            recs_text = " ".join(ai.get("dexterRecommendations", [])).lower()
            if any(w in recs_text for w in ["bekle", "düşüş", "çık", "sat", "realizasyon", "azalt"]):
                predicted_direction = "bearish"
            elif any(w in recs_text for w in ["al", "giriş", "artış", "yüksel", "güçlen"]):
                predicted_direction = "bullish"
            else:
                predicted_direction = "neutral"
            prediction = {
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "price_at_prediction": round(current_price, 6),
                "direction": predicted_direction,
                "recommendations": ai.get("dexterRecommendations", []),
                "verified_7d": None, "verified_14d": None, "verified_30d": None,
                "result_7d": None, "result_14d": None, "result_30d": None,
            }
            pred_ex = await session.execute(select(EvolverMemory).where(
                EvolverMemory.fund_code == fund_code,
                EvolverMemory.memory_type == "dexter_prediction",
                EvolverMemory.snapshot_date == datetime.utcnow().date()
            ))
            pred_rec = pred_ex.scalar_one_or_none()
            if pred_rec:
                pred_rec.content = json.dumps(prediction, ensure_ascii=False)
                pred_rec.last_seen = datetime.utcnow()
            else:
                session.add(EvolverMemory(
                    fund_code=fund_code,
                    memory_type="dexter_prediction",
                    content=json.dumps(prediction, ensure_ascii=False),
                    confidence=0.5,
                    snapshot_date=datetime.utcnow().date(),
                ))
            await session.commit()

    return {"success": True, "fundCode": fund_code,
            "aiInsights": ai.get("aiInsights", []),
            "dexterRecommendations": ai.get("dexterRecommendations", []),
            "twitterSummary": ai.get("twitterSummary", "")}


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


@app.post("/api/funds/{fund_code}/set-risk")
async def set_risk_score(fund_code: str, risk_score: int = Body(..., embed=True), fund_type: str = Body(None, embed=True)):
    fund_code = fund_code.upper()
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        values = {"risk_score": risk_score}
        if fund_type:
            values["fund_type"] = fund_type
        await session.execute(update(FundRecord).where(FundRecord.fund_code == fund_code).values(**values))
        await session.commit()
    return {"success": True, "fundCode": fund_code, "riskScore": risk_score}

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
            "aiInsights": json.loads(r.ai_insights or "[]"),
            "twitterSummary": r.twitter_summary,
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
    # Fiyat geçmişinden getiri hesapla
    prices = sorted(records, key=lambda x: x.date_key)
    prices_vals = [p.unit_price for p in prices if p.unit_price]
    def calc_return(prices, days):
        if len(prices) < 2: return None
        idx = max(0, len(prices) - days)
        p0, p1 = prices[idx], prices[-1]
        if not p0: return None
        return round((p1 - p0) / p0 * 100, 2)
    monthly_return = r.monthly_return if r.monthly_return is not None else calc_return(prices_vals, 21)
    yearly_return = r.yearly_return if r.yearly_return is not None else calc_return(prices_vals, 252)
    return {
        "code": fund_code, "name": r.fund_name,
        "latestDate": r.date_key, "unitPrice": r.unit_price,
        "totalValue": r.total_value, "participantCount": r.participant_count,
        "shareCount": r.share_count,
        "monthlyReturn": monthly_return, "yearlyReturn": yearly_return,
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
