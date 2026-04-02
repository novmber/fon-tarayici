"""
Haber Sinyal Modülü — Kural tabanlı + Ollama ile haber → fon sinyali
"""
import json
import httpx
from datetime import datetime

# Fon türü → ilgili haber anahtar kelimeleri
FUND_TYPE_KEYWORDS = {
    "altın": {
        "pozitif": ["altın yükseliyor", "altın artış", "ons yükseliş", "değerli metal", "altına talep", "gold"],
        "negatif": ["altın düşüyor", "altın geriledi", "ons düşüş", "altın satış"],
    },
    "hisse": {
        "pozitif": ["borsa yükseldi", "bist rekor", "hisse artış", "rallisi", "yükseliş trendinde", "güçlü büyüme"],
        "negatif": ["borsa düştü", "bist geriledi", "hisse satış", "sert düşüş", "panik satış", "resesyon"],
    },
    "tahvil": {
        "pozitif": ["faiz düşüyor", "faiz indirimi", "merkez bankası indirdi", "tahvil rallisi"],
        "negatif": ["faiz artıyor", "faiz artışı", "enflasyon yükseliyor", "tcmb faiz artırdı"],
    },
    "para piyasası": {
        "pozitif": ["faiz yüksek", "yüksek faiz", "mevduat cazibeli"],
        "negatif": ["faiz düşüyor", "faiz indirimi"],
    },
    "döviz": {
        "pozitif": ["dolar yükseldi", "euro arttı", "döviz güçlendi", "kur yükseliş"],
        "negatif": ["dolar düştü", "kur geriledi", "döviz zayıfladı"],
    },
    "serbest": {
        "pozitif": ["piyasalar güçlü", "risk iştahı arttı", "küresel rallisi"],
        "negatif": ["küresel satış", "risk iştahı azaldı", "jeopolitik risk"],
    },
}

# Genel piyasa sinyalleri — sadece çok net ifadeler
GENERAL_KEYWORDS = {
    "pozitif": ["borsa rekor kırdı", "enflasyon beklentinin altında", "faiz indirildi", "güçlü büyüme"],
    "negatif": ["borsa çöktü", "finansal kriz", "merkez bankası acil", "piyasalar çöküyor", "sert satış"],
    "uyarı": ["jeopolitik gerilim tırmandı", "savaş genişledi", "ani kur hareketi"],
}

def rule_based_signal(news_list: list, fund_type: str) -> dict:
    """Kural tabanlı haber sinyali üret"""
    fund_type_lower = (fund_type or "").lower()
    
    # Fon türüne göre anahtar kelimeler bul
    type_keywords = None
    for key in FUND_TYPE_KEYWORDS:
        if key in fund_type_lower:
            type_keywords = FUND_TYPE_KEYWORDS[key]
            break
    
    scores = {"pozitif": 0, "negatif": 0, "uyarı": 0}
    matched_news = []
    
    for news in news_list[:10]:
        text = (news.get("title", "") + " " + news.get("description", "")).lower()
        
        # Fon türüne özel kontrol
        if type_keywords:
            for keyword in type_keywords.get("pozitif", []):
                if keyword in text:
                    scores["pozitif"] += 2
                    matched_news.append({"news": news["title"][:60], "signal": "pozitif"})
                    break
            for keyword in type_keywords.get("negatif", []):
                if keyword in text:
                    scores["negatif"] += 2
                    matched_news.append({"news": news["title"][:60], "signal": "negatif"})
                    break
        
        # Genel kontrol
        for keyword in GENERAL_KEYWORDS["pozitif"]:
            if keyword in text:
                scores["pozitif"] += 1
        for keyword in GENERAL_KEYWORDS["negatif"]:
            if keyword in text:
                scores["negatif"] += 1
        for keyword in GENERAL_KEYWORDS["uyarı"]:
            if keyword in text:
                scores["uyarı"] += 1
    
    # Sinyal belirle
    dominant = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    confidence = scores[dominant] / max(total, 1)
    
    if total == 0:
        return {"signal": "nötr", "confidence": 0.5, "scores": scores, "matched": []}
    
    return {
        "signal": dominant if scores[dominant] > 0 else "nötr",
        "confidence": round(confidence, 2),
        "scores": scores,
        "matched": matched_news[:3],
        "source": "rule_based"
    }

async def ollama_news_signal(news_titles: list, fund_name: str, fund_type: str) -> dict:
    """Ollama ile haber sinyali üret"""
    titles_text = "\n".join([f"- {t}" for t in news_titles[:8]])
    prompt = f"""Sen bir fon analisti yardımcısısın. Aşağıdaki haber başlıklarını değerlendirerek "{fund_name}" ({fund_type}) yatırım fonu için kısa vadeli etki sinyali üret.

Haberler:
{titles_text}

Sadece JSON formatında yanıt ver, başka bir şey yazma:
{{"signal": "pozitif|negatif|nötr|uyarı", "confidence": 0.0-1.0, "reason": "kısa açıklama (max 100 karakter)"}}"""

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post("http://localhost:11434/api/generate", json={
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 100}
            })
            text = resp.json().get("response", "")
            # JSON parse
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                result["source"] = "ollama"
                return result
    except Exception as e:
        print(f"Ollama error: {e}")
    
    return None

async def get_news_signal(news_list: list, fund_name: str, fund_type: str) -> dict:
    """Ana sinyal fonksiyonu — önce kural, sonra Ollama"""
    default = {"signal": "nötr", "confidence": 0.5, "matched": [], "source": "rule_based", "reason": ""}
    
    try:
        rule_result = rule_based_signal(news_list, fund_type)
        rule_result.setdefault("reason", "")
        rule_result.setdefault("source", "rule_based")
        rule_result.setdefault("matched", [])
        
        # Ollama devre dışı — CPU yük çok yüksek
        # Sadece kural tabanlı kullan
        
        return rule_result
    except Exception as e:
        print(f"get_news_signal error: {e}")
        return default

if __name__ == "__main__":
    import asyncio
    # Test
    test_news = [
        {"title": "Altın yükseliyor, ons 3000 doları aştı", "description": "Altın fiyatları rekor kırdı"},
        {"title": "Faiz artışı beklentisi piyasaları sarstı", "description": "Merkez bankası faiz kararı"},
    ]
    result = asyncio.run(get_news_signal(test_news, "Test Altın Fonu", "Altın Fonu"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
