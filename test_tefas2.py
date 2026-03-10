"""
TEFAS Request Format Araştırması
"""
import urllib.request
import urllib.parse
import json

HEADERS_GET = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Referer": "https://www.tefas.gov.tr/FonAnaliz.aspx",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

HEADERS_POST = {**HEADERS_GET, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

FON = "MTH"

def fetch_get(url, label):
    req = urllib.request.Request(url, headers=HEADERS_GET)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8")
            print(f"\n{'='*60}")
            print(f"✅ GET {label}")
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    print(f"   Liste uzunluğu: {len(data)}")
                    if data:
                        print(f"   İlk eleman alanları: {list(data[0].keys())}")
                        # MTH'yi bul
                        mth = [x for x in data if x.get("FonKodu") == FON or x.get("FONKODU") == FON or x.get("FundCode") == FON]
                        if mth:
                            print(f"   MTH verisi: {json.dumps(mth[0], ensure_ascii=False, indent=2)}")
                        else:
                            print(f"   İlk 2 eleman: {json.dumps(data[:2], ensure_ascii=False, indent=2)}")
                elif isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                    if "data" in data:
                        d = data["data"]
                        print(f"   data uzunluğu: {len(d)}")
                        if d:
                            print(f"   İlk eleman: {json.dumps(d[0], ensure_ascii=False, indent=2)}")
            except:
                print(f"   Ham yanıt (ilk 500): {raw[:500]}")
    except Exception as e:
        print(f"\n❌ GET {label}: {e}")

def fetch_post(url, payload, label):
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, headers=HEADERS_POST, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8")
            print(f"\n{'='*60}")
            print(f"✅ POST {label}")
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    print(f"   Liste uzunluğu: {len(parsed)}")
                    if parsed:
                        print(f"   Alanlar: {list(parsed[0].keys())}")
                        mth = [x for x in parsed if FON in str(x)]
                        if mth:
                            print(f"   MTH verisi: {json.dumps(mth[0], ensure_ascii=False, indent=2)}")
                        else:
                            print(f"   İlk eleman: {json.dumps(parsed[0], ensure_ascii=False, indent=2)}")
                elif isinstance(parsed, dict):
                    print(f"   Keys: {list(parsed.keys())}")
                    if "data" in parsed and parsed["data"]:
                        print(f"   İlk data: {json.dumps(parsed['data'][0], ensure_ascii=False, indent=2)}")
                    else:
                        print(f"   Yanıt: {json.dumps(parsed, ensure_ascii=False)[:500]}")
            except:
                print(f"   Ham yanıt: {raw[:500]}")
    except Exception as e:
        print(f"\n❌ POST {label}: {e}")

# ── Mevcut çalışan endpoint (BindHistoryInfo) doğru format ──
fetch_post(
    "https://www.tefas.gov.tr/api/DB/BindHistoryInfo",
    {"fontip": "YAT", "fonkod": FON, "bastarih": "01.02.2026", "bittarih": "08.03.2026"},
    "BindHistoryInfo POST - fiyat geçmişi"
)

# ── Portföy dağılımı ──
fetch_post(
    "https://www.tefas.gov.tr/api/DB/BindHistoryAllocation",
    {"fontip": "YAT", "fonkod": FON, "bastarih": "01.02.2026", "bittarih": "08.03.2026"},
    "BindHistoryAllocation POST - portföy dağılımı"
)

# ── Fon detay (tek fon) ──
fetch_post(
    "https://www.tefas.gov.tr/api/DB/BindFundInfo",
    {"fonkod": FON},
    "BindFundInfo POST"
)

# ── Alternatif: BindComparisonFundInfo ──
fetch_post(
    "https://www.tefas.gov.tr/api/DB/BindComparisonFundInfo",
    {"fonkod": FON},
    "BindComparisonFundInfo POST"
)

# ── Fon özet (tek satır detay) ──
fetch_get(
    f"https://www.tefas.gov.tr/api/DB/BindFundInfo?fonkod={FON}&fontur=YAT",
    "BindFundInfo GET fontur=YAT"
)

# ── Holdings / portföy içeriği ──
fetch_post(
    "https://www.tefas.gov.tr/api/DB/BindFundPortfolio",
    {"fonkod": FON},
    "BindFundPortfolio POST"
)

fetch_post(
    "https://www.tefas.gov.tr/api/DB/BindHistoryInfo",
    {"fontip": "YAT", "fonkod": FON, "bastarih": "01.03.2026", "bittarih": "08.03.2026"},
    "BindHistoryInfo - KISISAYISI alanı var mı? (son 1 hafta)"
)
