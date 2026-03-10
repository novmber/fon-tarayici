"""
TEFAS Endpoint Test Scripti
Çalıştır: python3 test_tefas.py
"""
import urllib.request
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.tefas.gov.tr/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

FON = "MTH"

def fetch(url, label):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
            print(f"\n{'='*60}")
            print(f"✅ {label}")
            print(f"   URL: {url}")
            if "data" in data and data["data"]:
                ilk = data["data"][0]
                print(f"   Toplam kayıt: {len(data['data'])}")
                print(f"   Alanlar: {list(ilk.keys())}")
                print(f"   İlk kayıt:\n{json.dumps(ilk, ensure_ascii=False, indent=4)}")
            else:
                print(f"   Yanıt: {json.dumps(data, ensure_ascii=False)[:1000]}")
    except Exception as e:
        print(f"\n❌ {label}")
        print(f"   Hata: {e}")

print(f"TEFAS Endpoint Testleri - Fon: {FON}")
print("="*60)

# 1. Fiyat + temel bilgiler (günlük)
fetch(
    f"https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
    f"?fontip=YAT&fonkod={FON}&bastarih=01.01.2025&bittarih=08.03.2026",
    "1. BindHistoryInfo — Fiyat, portföy büyüklüğü, pay adedi"
)

# 2. Portföy dağılımı (tarihsel)
fetch(
    f"https://www.tefas.gov.tr/api/DB/BindHistoryAllocation"
    f"?fontip=YAT&fonkod={FON}&bastarih=01.01.2025&bittarih=08.03.2026",
    "2. BindHistoryAllocation — Portföy dağılım yüzdeleri"
)

# 3. Fon detay / meta
fetch(
    f"https://www.tefas.gov.tr/api/DB/BindFundInfo?fonkod={FON}",
    "3. BindFundInfo — Risk, ücret, valör, stopaj meta bilgisi"
)

# 4. Alternatif: fon arama
fetch(
    f"https://www.tefas.gov.tr/api/DB/BindFundList?fonkod={FON}",
    "4. BindFundList — Fon listesi / arama"
)

# 5. Katılımcı sayısı ayrı endpoint dene
fetch(
    f"https://www.tefas.gov.tr/api/DB/BindParticipantInfo?fonkod={FON}",
    "5. BindParticipantInfo — Katılımcı sayısı"
)

# 6. Fonun izahname/detay sayfası API
fetch(
    f"https://www.tefas.gov.tr/FonAnaliz.aspx?fonkod={FON}",
    "6. FonAnaliz sayfası (HTML)"
)
