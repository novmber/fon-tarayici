"""
TEFAS async client — curl_cffi AsyncSession
subprocess yerine doğrudan import edilir.
"""
import asyncio, random
from datetime import datetime, timedelta
from curl_cffi.requests import AsyncSession

BASE = "https://www.tefas.gov.tr"
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

ALLOC_LABELS = {
    "hs": "Hisse Senedi", "yhs": "Yabancı Hisse", "dt": "Devlet Tahvili",
    "hb": "Hazine Bonosu", "tpp": "Tahvil/Bono TPP", "bpp": "Tahvil/Bono BPP",
    "tr": "Ters Repo", "r": "Repo", "vdm": "Vadeli Mevduat", "vm": "Vadesiz Mevduat",
    "vmtl": "Vadeli Mevduat TL", "km": "Kıymetli Maden", "byf": "BYF",
    "yyf": "Yabancı Yatırım Fonu", "osks": "Özel Sektör Kira Sertifikası",
    "ost": "Özel Sektör Tahvili", "fb": "Finansman Bonosu",
    "kks": "Kamu Kira Sertifikası", "kkstl": "Kamu Kira Sertifikası TL",
    "ybyf": "Yabancı BYF", "vint": "Diğer", "vmd": "Döviz Mevduat",
}

# ── Rate limiting sabitleri ──────────────────────────────────────────────────
SLEEP_BETWEEN_CHUNKS  = (3, 6)  # başarılı chunk arası (sn)
SLEEP_ON_EMPTY        = 15      # boş yanıt — soft-ban sinyali (sn)
SLEEP_ON_FUND_TYPE    = (2, 4)  # fonTipi denemeleri arası (sn)
SESSION_REFRESH_EVERY = 4       # kaç chunk'ta bir session yenilenir

# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _parse_date(s: str) -> datetime:
    s = s.strip()
    if len(s) == 10 and s[4] == "-":
        return datetime.strptime(s, "%Y-%m-%d")
    s = s.replace("-", "")
    if len(s) == 8:
        return datetime.strptime(s, "%Y%m%d")
    if "." in s:
        return datetime.strptime(s, "%d.%m.%Y")
    raise ValueError(f"Tanımsız tarih formatı: {s}")

def _monthly_chunks(start_dt: datetime, end_dt: datetime):
    import calendar
    current = start_dt.replace(day=1)
    while current <= end_dt:
        last_day = calendar.monthrange(current.year, current.month)[1]
        chunk_end = min(current.replace(day=last_day), end_dt)
        chunk_start = max(current, start_dt)
        yield chunk_start, chunk_end
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1, day=1)
        else:
            current = current.replace(month=current.month + 1, day=1)

# ── Session yönetimi ─────────────────────────────────────────────────────────

async def _make_session(fund_type: str = "YAT") -> AsyncSession:
    """Chrome impersonation + cookie alma."""
    s = AsyncSession(impersonate="chrome131")
    s.headers.update({"User-Agent": CHROME_UA, "Accept-Language": "tr-TR,tr;q=0.9"})
    await s.get(
        f"{BASE}/tr/fon-verileri?fundType={fund_type}",
        headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
        timeout=30,
    )
    await asyncio.sleep(random.uniform(1.5, 2.5))  # cookie yerleşsin
    return s

async def _post(session: AsyncSession, path: str, payload: dict) -> list:
    res = await session.post(
        f"{BASE}{path}",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Referer": f"{BASE}/tr/fon-verileri",
            "Origin": BASE,
        },
        timeout=30,
    )
    d = res.json()
    return d.get("resultList") or []

# ── Ana fonksiyonlar ─────────────────────────────────────────────────────────

async def fetch_history(
    fonkod: str,
    bastarih: str = None,
    bittarih: str = None,
    days: int = 365,
) -> list:
    end_dt   = _parse_date(bittarih) if bittarih else datetime.now()
    start_dt = _parse_date(bastarih) if bastarih else end_dt - timedelta(days=days)

    session      = await _make_session()
    all_data     = []
    empty_streak = 0
    chunk_count  = 0

    try:
        for chunk_start, chunk_end in _monthly_chunks(start_dt, end_dt):
            # Önleyici session yenileme
            if chunk_count > 0 and chunk_count % SESSION_REFRESH_EVERY == 0:
                await session.close()
                session = await _make_session()
                await asyncio.sleep(random.uniform(2, 4))

            bas = chunk_start.strftime("%Y%m%d")
            bit = chunk_end.strftime("%Y%m%d")

            try:
                items = await _post(session, "/api/funds/fonGnlBlgSiraliGetir", {
                    "fonTipi": "YAT", "fonKodu": fonkod, "aramaMetni": fonkod,
                    "fonTurKod": None, "fonGrubu": None, "sfonTurKod": None,
                    "basTarih": bas, "bitTarih": bit,
                    "basSira": 1, "bitSira": 1000,
                    "fonTurAciklama": None, "dil": "TR", "kurucuKod": None,
                })
            except Exception:
                items = []

            if not items:
                empty_streak += 1
                if empty_streak >= 3:
                    # Soft-ban — session yenile
                    await session.close()
                    session = await _make_session()
                    empty_streak = 0
                await asyncio.sleep(SLEEP_ON_EMPTY)
            else:
                empty_streak = 0
                for x in items:
                    if x.get("fonKodu") != fonkod:
                        continue
                    if x.get("fiyat") and float(x["fiyat"]) > 0:
                        all_data.append({
                            "TARIH":           x["tarih"],
                            "FIYAT":           x["fiyat"],
                            "FONUNVAN":        x.get("fonUnvan", fonkod),
                            "PORTFOYBUYUKLUK": x.get("portfoyBuyukluk") or 0,
                            "KISISAYISI":      x.get("kisiSayisi") or 0,
                            "TEDPAYSAYISI":    x.get("tedPaySayisi") or 0,
                        })
                await asyncio.sleep(random.uniform(*SLEEP_BETWEEN_CHUNKS))

            chunk_count += 1
    finally:
        await session.close()

    return all_data


async def fetch_fund_info(fonkod: str) -> dict:
    """Risk değeri + dönemsel getiri — tek session ile tüm fonTipi denemeleri."""
    FUND_TYPES = ["YAT", "EMK", "BYF", "GYF", "GSYF"]
    session = await _make_session()
    try:
        for ft in FUND_TYPES:
            try:
                items = await _post(session, "/api/funds/fonGetiriBazliBilgiGetir", {
                    "dil": "TR", "fonTipi": ft, "kurucuKodu": None,
                    "sfonTurKod": None, "fonTurAciklama": None, "islem": 1,
                    "fonTurKod": None, "fonGrubu": None,
                    "donemGetiri1a": "1", "donemGetiri3a": "1", "donemGetiri6a": "1",
                    "donemGetiri1y": "1", "donemGetiriyb": "1",
                    "donemGetiri3y": "1", "donemGetiri5y": "1",
                    "basTarih": None, "bitTarih": None,
                    "calismaTipi": 2, "getiriOrani": "1",
                    "basSira": 1, "bitSira": 2000,
                    "aramaMetni": fonkod, "fonKodu": fonkod,
                })
            except Exception:
                items = []

            match = [x for x in items if x.get("fonKodu") == fonkod]
            if match:
                x = match[0]
                return {
                    "FONUNVAN":   x.get("fonUnvan", fonkod),
                    "FONTUR":     x.get("fonTurAciklama", ""),
                    "RISKDEGERI": int(x.get("riskDegeri") or 0),
                    "getiri1a":   x.get("getiri1a"),
                    "getiri3a":   x.get("getiri3a"),
                    "getiri6a":   x.get("getiri6a"),
                    "getiri1y":   x.get("getiri1y"),
                    "getiriyb":   x.get("getiriyb"),
                    "getiri3y":   x.get("getiri3y"),
                    "getiri5y":   x.get("getiri5y"),
                }
            # Bulunamadı — bir sonraki fonTipi'ne geçmeden bekle
            await asyncio.sleep(random.uniform(*SLEEP_ON_FUND_TYPE))
    finally:
        await session.close()

    return {}


async def fetch_allocation(
    fonkod: str,
    bastarih: str = None,
    bittarih: str = None,
) -> dict:
    end_dt   = _parse_date(bittarih) if bittarih else datetime.now()
    start_dt = _parse_date(bastarih) if bastarih else end_dt - timedelta(days=7)
    bas = start_dt.strftime("%Y%m%d")
    bit = end_dt.strftime("%Y%m%d")

    session = await _make_session()
    try:
        items = await _post(session, "/api/funds/dagilimSiraliGetirT", {
            "fonTipi": "YAT", "fonKodu": fonkod, "aramaMetni": fonkod,
            "fonTurKod": None, "fonGrubu": None, "sfonTurKod": None,
            "basTarih": bas, "bitTarih": bit,
            "basSira": 1, "bitSira": 10,
            "fonTurAciklama": None, "dil": "TR", "kurucuKod": None,
        })
    finally:
        await session.close()

    result = {}
    for x in items:
        d = str(x.get("tarih", ""))[:10]
        if not d:
            continue
        alloc = [
            {"name": ALLOC_LABELS.get(k, k), "value": round(float(v), 2)}
            for k, v in x.items()
            if k not in ("fonKodu", "fonUnvan", "tarih", "bilFiyat", "rn")
            and v is not None and float(v) > 0
        ]
        result[d] = sorted(alloc, key=lambda a: -a["value"])

    return result


async def fetch_top_holdings(fonkod: str, days: int = 7) -> list:
    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    bas = start_dt.strftime("%d.%m.%Y")
    bit = end_dt.strftime("%d.%m.%Y")

    session = await _make_session()
    try:
        items = await _post(session, "/api/funds/fonPortfoyGetir", {
            "fonTipi": "YAT", "fonKodu": fonkod,
            "basTarih": bas, "bitTarih": bit,
            "dil": "TR",
        })
        if not items:
            items = await _post(session, "/api/funds/dagilimDetayGetirT", {
                "fonTipi": "YAT", "fonKodu": fonkod,
                "basTarih": bas, "bitTarih": bit,
                "dil": "TR", "basSira": 1, "bitSira": 10,
            })
    finally:
        await session.close()

    if not items:
        return []

    latest = items[-1]
    holdings = []
    for i in range(1, 11):
        name   = latest.get(f"VARLIKADI{i}", "") or latest.get(f"varlikAdi{i}", "")
        weight = latest.get(f"YUZDE{i}", 0)      or latest.get(f"yuzde{i}", 0)
        if name and float(weight or 0) > 0:
            holdings.append({"name": name, "weight": round(float(weight), 2)})

    return holdings
