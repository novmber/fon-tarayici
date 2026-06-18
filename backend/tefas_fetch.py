"""
TEFAS veri çekici — Yeni API (Mayıs 2026)
curl_cffi ile Chrome impersonation — WAF bypass
Max 1 aylık chunk — otomatik parçalama
"""
import sys, json, time, random
from datetime import datetime, timedelta
from curl_cffi import requests as cr

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
BASE = "https://www.tefas.gov.tr"
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

# --- Rate limiting sabitleri ---
SLEEP_BETWEEN_CHUNKS = (3, 6)   # chunk arası rastgele bekleme (sn)
SLEEP_ON_EMPTY       = 15       # boş yanıt gelince bekleme (sn) — soft-ban sinyali
SLEEP_ON_ERROR       = 30       # hata bekleme (sn)
MAX_EMPTY_STREAK     = 3        # kaç ardışık boş chunk sonra session yenilenir
SESSION_REFRESH_EVERY = 4       # kaç chunk'ta bir session yenilenir (önleyici)

def _session(fund_type="YAT"):
    s = cr.Session(impersonate="chrome131")
    s.headers.update({"User-Agent": CHROME_UA, "Accept-Language": "tr-TR,tr;q=0.9"})
    # Ana sayfayı ziyaret et — cookie + token al
    s.get(f"{BASE}/tr/fon-verileri?fundType={fund_type}",
          headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}, timeout=30)
    time.sleep(random.uniform(1.5, 2.5))  # sayfanın "yüklenmesini bekle"
    return s

def _post(session, path, payload):
    res = session.post(f"{BASE}{path}", json=payload,
        headers={"Content-Type": "application/json",
                 "Referer": f"{BASE}/tr/fon-verileri",
                 "Origin": BASE}, timeout=30)
    d = res.json()
    return d.get("resultList") or []

def _monthly_chunks(start_dt, end_dt):
    """1 aylık chunk'lara böl"""
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

def _parse_date(s):
    """YYYYMMDD veya DD.MM.YYYY → datetime"""
    s = s.strip().replace("-", "")
    if len(s) == 8:
        return datetime.strptime(s, "%Y%m%d")
    if "." in s:
        return datetime.strptime(s, "%d.%m.%Y")
    return datetime.strptime(s, "%Y%m%d")


def fetch_history(fonkod: str, bastarih: str = None, bittarih: str = None) -> dict:
    """Fiyat + portföy + yatırımcı — aylık chunk ile"""
    end_dt   = _parse_date(bittarih) if bittarih else datetime.now()
    start_dt = _parse_date(bastarih) if bastarih else end_dt - timedelta(days=365)

    s = _session()
    all_data     = []
    empty_streak = 0   # ardışık boş yanıt sayacı
    chunk_count  = 0   # toplam chunk sayacı

    for chunk_start, chunk_end in _monthly_chunks(start_dt, end_dt):
        bas = chunk_start.strftime("%Y%m%d")
        bit = chunk_end.strftime("%Y%m%d")

        # Önleyici session yenileme
        if chunk_count > 0 and chunk_count % SESSION_REFRESH_EVERY == 0:
            s = _session()
            time.sleep(random.uniform(2, 4))

        try:
            items = _post(s, "/api/funds/fonGnlBlgSiraliGetir", {
                "fonTipi": "YAT", "fonKodu": fonkod, "aramaMetni": fonkod,
                "fonTurKod": None, "fonGrubu": None, "sfonTurKod": None,
                "basTarih": bas, "bitTarih": bit,
                "basSira": 1, "bitSira": 1000,
                "fonTurAciklama": None, "dil": "TR", "kurucuKod": None,
            })
        except Exception:
            time.sleep(SLEEP_ON_ERROR)
            items = []

        if not items:
            # Boş yanıt = soft-ban veya gerçekten veri yok
            empty_streak += 1
            if empty_streak >= MAX_EMPTY_STREAK:
                # Session tükenmişe benzedi, yenile
                s = _session()
                empty_streak = 0
                time.sleep(SLEEP_ON_EMPTY)
            else:
                time.sleep(SLEEP_ON_EMPTY)
        else:
            empty_streak = 0
            for x in items:
                if x.get("fonKodu") != fonkod:
                    continue
                if x.get("fiyat") and float(x["fiyat"]) > 0:
                    all_data.append({
                        "TARIH":            x["tarih"],
                        "FIYAT":            x["fiyat"],
                        "FONUNVAN":         x.get("fonUnvan", fonkod),
                        "PORTFOYBUYUKLUK":  x.get("portfoyBuyukluk") or 0,
                        "KISISAYISI":       x.get("kisiSayisi") or 0,
                        "TEDPAYSAYISI":     x.get("tedPaySayisi") or 0,
                    })
            # Başarılı chunk — normal bekleme
            time.sleep(random.uniform(*SLEEP_BETWEEN_CHUNKS))

        chunk_count += 1

    return {"data": all_data}


def fetch_fund_info(fonkod: str) -> dict:
    """Risk değeri + getiri bilgileri"""
    # Tek session aç, tüm fonTipi denemelerinde yeniden kullan
    s = _session()

    def _try(session, fon_tipi):
        return _post(session, "/api/funds/fonGetiriBazliBilgiGetir", {
            "dil": "TR", "fonTipi": fon_tipi, "kurucuKodu": None,
            "sfonTurKod": None, "fonTurAciklama": None, "islem": 1,
            "fonTurKod": None, "fonGrubu": None,
            "donemGetiri1a": "1", "donemGetiri3a": "1", "donemGetiri6a": "1",
            "donemGetiri1y": "1", "donemGetiriyb": "1", "donemGetiri3y": "1", "donemGetiri5y": "1",
            "basTarih": None, "bitTarih": None, "calismaTipi": 2, "getiriOrani": "1",
            "basSira": 1, "bitSira": 2000, "aramaMetni": fonkod, "fonKodu": fonkod,
        })

    match = []
    for ft in ["YAT", "EMK", "BYF", "GYF", "GSYF"]:
        items = _try(s, ft)
        match = [x for x in items if x.get("fonKodu") == fonkod]
        if match:
            break
        time.sleep(random.uniform(2, 4))  # fonTipi denemeleri arası bekleme

    if not match:
        return {}
    x = match[0]
    return {
        "FONUNVAN":  x.get("fonUnvan", fonkod),
        "FONTUR":    x.get("fonTurAciklama", ""),
        "RISKDEGERI": int(x.get("riskDegeri") or 0),
        "getiri1a":  x.get("getiri1a"),
        "getiri3a":  x.get("getiri3a"),
        "getiri6a":  x.get("getiri6a"),
        "getiri1y":  x.get("getiri1y"),
        "getiriyb":  x.get("getiriyb"),
        "getiri3y":  x.get("getiri3y"),
        "getiri5y":  x.get("getiri5y"),
    }


def fetch_allocation(fonkod: str, bastarih: str = None, bittarih: str = None) -> dict:
    """Varlık dağılımı — son 7 gün"""
    end_dt   = _parse_date(bittarih) if bittarih else datetime.now()
    start_dt = _parse_date(bastarih) if bastarih else end_dt - timedelta(days=7)
    bas = start_dt.strftime("%Y%m%d")
    bit = end_dt.strftime("%Y%m%d")

    s = _session()
    items = _post(s, "/api/funds/dagilimSiraliGetirT", {
        "fonTipi": "YAT", "fonKodu": fonkod, "aramaMetni": fonkod,
        "fonTurKod": None, "fonGrubu": None, "sfonTurKod": None,
        "basTarih": bas, "bitTarih": bit,
        "basSira": 1, "bitSira": 10,
        "fonTurAciklama": None, "dil": "TR", "kurucuKod": None,
    })
    result = {}
    for x in items:
        d = str(x.get("tarih", ""))[:10]
        if not d:
            continue
        alloc = [{"name": ALLOC_LABELS.get(k, k), "value": round(float(v), 2)}
                 for k, v in x.items()
                 if k not in ("fonKodu", "fonUnvan", "tarih", "bilFiyat", "rn")
                 and v is not None and float(v) > 0]
        result[d] = sorted(alloc, key=lambda a: -a["value"])
    return result


def fetch(endpoint: str, fonkod: str, bastarih: str = "", bittarih: str = "") -> dict:
    if endpoint == "BindHistoryInfo":
        return fetch_history(fonkod, bastarih or None, bittarih or None)
    elif endpoint == "BindFundInfo":
        return {"data": [fetch_fund_info(fonkod)]}
    elif endpoint == "BindHistoryAllocation":
        alloc = fetch_allocation(fonkod, bastarih or None, bittarih or None)
        return {"data": alloc}
    return {"data": []}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Kullanim: tefas_fetch.py <endpoint> <fonkod>"}))
        sys.exit(1)
    _, endpoint, fonkod = sys.argv[:3]
    bastarih = sys.argv[3] if len(sys.argv) > 3 else ""
    bittarih = sys.argv[4] if len(sys.argv) > 4 else ""
    try:
        result = fetch(endpoint, fonkod, bastarih, bittarih)
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(json.dumps({"error": str(e), "data": []}))
        sys.stdout.flush()
        sys.exit(1)
