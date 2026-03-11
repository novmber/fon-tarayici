"""
TEFAS veri çekici — WAF bypass için tarayıcı header'ları ile
Kullanım: python3 tefas_fetch.py <endpoint> <fonkod> <bastarih> <bittarih>
Örnek:    python3 tefas_fetch.py BindHistoryInfo TLY 01.01.2025 09.03.2026
"""
import sys, json, urllib.request, urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Referer": "https://www.tefas.gov.tr/FonAnaliz.aspx",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

def fetch(endpoint: str, fonkod: str, bastarih: str, bittarih: str) -> dict:
    url = f"https://www.tefas.gov.tr/api/DB/{endpoint}"
    fontip_list = ["YAT", "EMK", ""] if endpoint == "BindFundInfo" else ["YAT"]
    for fontip in fontip_list:
        payload_dict = {"fonkod": fonkod, "bastarih": bastarih, "bittarih": bittarih}
        if fontip:
            payload_dict["fontip"] = fontip
        payload = urllib.parse.urlencode(payload_dict).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        if not raw.strip() or raw.strip().startswith("<"):
            continue
        result = json.loads(raw)
        if result.get("data"):
            return result
    return {"data": []}


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(json.dumps({"error": "Eksik argüman"}))
        sys.exit(1)

    _, endpoint, fonkod, bastarih, bittarih = sys.argv[:5]
    try:
        result = fetch(endpoint, fonkod, bastarih, bittarih)
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(json.dumps({"error": str(e), "data": []}))
        sys.stdout.flush()
        sys.exit(1)
