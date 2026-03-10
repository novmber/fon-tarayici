# 📡 Fon Tarayıcı

KAP Fon Analiz Platformu — FastAPI + React + SQLite + Anthropic AI

---

## 🚀 Kurulum (Ubuntu)

### 1. Gereksinimler

```bash
# Python 3.10+
python3 --version

# Node.js 18+ ve npm
node --version
npm --version

# Yoksa kur:
sudo apt update
sudo apt install -y python3-pip nodejs npm
```

### 2. Projeyi İndir / Kopyala

```bash
# Proje klasörüne gir
cd fon-tarayici
```

### 3. API Key Ekle

`.env` dosyasını düzenle:

```bash
nano .env
```

İçeriği şu şekilde olmalı:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx
```

### 4. Çalıştır

```bash
chmod +x start.sh
./start.sh
```

Tarayıcıda aç: **http://localhost:9000**

---

## 🔧 Geliştirme Modu

Backend (9000) ve Frontend (5173) ayrı ayrı çalışır, hot-reload aktif:

```bash
chmod +x dev.sh
./dev.sh
```

---

## 📁 Proje Yapısı

```
fon-tarayici/
├── backend/
│   ├── main.py          # FastAPI uygulaması
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js       # Backend API client
│   │   └── components/
│   │       ├── FundCard.jsx
│   │       ├── FundDetail.jsx
│   │       ├── UploadZone.jsx
│   │       └── Spinner.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── data/
│   └── fon.db           # SQLite database (otomatik oluşur)
├── .env                 # API Key
├── start.sh             # Tek komutla başlat
└── dev.sh               # Geliştirme modu
```

---

## 🗄️ Database Yapısı

### `fund_records` tablosu
Her yüklenen PDF için bir kayıt — fon kodu + ay bazlı unique.

| Alan | Açıklama |
|------|----------|
| fund_code | PBR, AAK, HFB vb. |
| month_key | 2026-01 formatı |
| unit_price | Pay fiyatı |
| monthly_return | Aylık getiri % |
| portfolio_items | JSON — pie chart verisi |
| ai_insights | JSON — AI tespitleri |
| dexter_recommendations | JSON — Dexter önerileri |

### `evolver_memory` tablosu
Fon bazlı öğrenilen pattern'lar:

| Tip | Açıklama |
|-----|----------|
| pattern | Ortalama getiri, trend, gözlem sayısı |
| insight | Tekrar eden AI tespitleri (güven artar) |

---

## 📡 API Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/upload` | PDF yükle + analiz |
| GET | `/api/funds` | Tüm fonlar |
| GET | `/api/funds/{code}` | Tek fon detayı |
| DELETE | `/api/funds/{code}/months/{key}` | Ay sil |
| DELETE | `/api/funds/{code}` | Fon sil |
| GET | `/api/evolver/{code}` | Evolver hafızası |
| GET | `/api/stats` | Genel istatistikler |
| GET | `/docs` | Swagger UI |

---

## 🤖 Evolver Sistemi

Her PDF yüklendiğinde:

1. **Yeni analiz** yapılır
2. **Geçmiş dönemler** context olarak Claude'a gönderilir
3. **Evolver hafızası** okunur (pattern + tekrar eden tespitler)
4. **Daha isabetli** Dexter önerileri üretilir
5. **Hafıza güncellenir** — tekrar gören insights'ların confidence'ı artar

Confidence değeri: 0.4 → 0.99 (her tekrarda +0.1)

---

## 🐛 Sorun Giderme

```bash
# Port 9000 meşgulse
kill $(lsof -ti:9000)

# Database sıfırla
rm data/fon.db

# Log görüntüle
cd backend && python main.py 2>&1 | tee ../logs.txt
```
