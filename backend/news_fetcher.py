"""
Haber modülü — RSS kaynaklarından fon/piyasa haberleri çeker
"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

RSS_FEEDS = [
    ("Bloomberg HT", "https://www.bloomberght.com/rss"),
    ("Ekonomim", "https://www.ekonomim.com/rss"),
    ("Dünya Gazetesi", "https://www.dunya.com/rss"),
    ("Para Analiz", "https://www.paraanaliz.com/feed/"),
]

# Fon ve piyasa anahtar kelimeleri
FUND_KEYWORDS = [
    "yatırım fonu", "fon", "tefas", "portföy",
    "hisse senedi", "borsa", "bist", "faiz",
    "enflasyon", "dolar", "euro", "altın", "gümüş",
    "merkez bankası", "tcmb", "kap"
]

def fetch_rss(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        res = urllib.request.urlopen(req, timeout=8)
        return res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"RSS fetch error {url}: {e}")
        return None

def parse_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return datetime.now().strftime('%Y-%m-%d %H:%M')

def is_relevant(title: str, description: str = '') -> bool:
    text = (title + ' ' + description).lower()
    return any(kw in text for kw in FUND_KEYWORDS)

def score_relevance(title: str, description: str = '') -> int:
    text = (title + ' ' + description).lower()
    return sum(1 for kw in FUND_KEYWORDS if kw in text)

def fetch_all_news(limit: int = 30) -> list:
    all_news = []
    for source, url in RSS_FEEDS:
        xml = fetch_rss(url)
        if not xml:
            continue
        try:
            root = ET.fromstring(xml)
            items = root.findall('.//item')
            for item in items:
                title = item.findtext('title', '').strip()
                link = item.findtext('link', '').strip()
                desc = item.findtext('description', '').strip()
                pub_date = item.findtext('pubDate', '')
                
                # HTML tag'lerini temizle
                desc_clean = re.sub(r'<[^>]+>', '', desc)[:200]
                
                if not title or not link:
                    continue
                
                relevance = score_relevance(title, desc_clean)
                
                all_news.append({
                    'source': source,
                    'title': title,
                    'link': link,
                    'description': desc_clean,
                    'date': parse_date(pub_date),
                    'relevance': relevance,
                    'relevant': relevance > 0
                })
        except Exception as e:
            print(f"Parse error {source}: {e}")
    
    # Relevance skora göre sırala
    all_news.sort(key=lambda x: (-x['relevance'], x['date']), reverse=False)
    all_news.sort(key=lambda x: x['relevance'], reverse=True)
    
    return all_news[:limit]

def fetch_fund_news(fund_name: str, fund_code: str, limit: int = 5) -> list:
    """Belirli bir fon için alakalı haberleri getir"""
    all_news = fetch_all_news(100)
    fund_keywords = [
        fund_code.lower(),
        fund_name.lower()[:20],
    ]
    # Fon adından önemli kelimeleri çıkar
    for word in fund_name.lower().split():
        if len(word) > 4 and word not in ['portföy', 'fonu', 'birinci', 'ikinci']:
            fund_keywords.append(word)
    
    fund_news = []
    for news in all_news:
        text = (news['title'] + ' ' + news['description']).lower()
        if any(kw in text for kw in fund_keywords):
            fund_news.append(news)
    
    # Fona özel haber yoksa genel finans haberlerini döndür
    if not fund_news:
        fund_news = [n for n in all_news if n['relevant']][:limit]
    
    return fund_news[:limit]

if __name__ == '__main__':
    print("📰 Haberler çekiliyor...")
    news = fetch_all_news(20)
    relevant = [n for n in news if n['relevant']]
    print(f"Toplam: {len(news)}, İlgili: {len(relevant)}")
    for n in relevant[:5]:
        print(f"\n[{n['source']}] {n['title'][:70]}")
        print(f"  Skor: {n['relevance']} | {n['date']}")
