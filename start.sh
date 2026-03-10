#!/bin/bash
# ─── Fon Tarayıcı - Kurulum ve Çalıştırma ────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ___         _____              _      "
echo " | __| ___   |_   _|__ _ _ __ _(_)__ _"
echo " | _| / _ \    | |/ _\` | '_/ _\` | / _\` |"
echo " |_|  \___/    |_|\__,_|_| \__,_|_\__,_|"
echo -e "${NC}"
echo -e "${YELLOW}KAP Fon Analiz Platformu — 0.0.0.0:9009${NC}"
echo ""

# .env kontrolü
if [ ! -f ".env" ]; then
    echo -e "${RED}⚠️  .env dosyası bulunamadı!${NC}"
    exit 1
fi

if grep -q "buraya-keyinizi-girin" .env 2>/dev/null; then
    echo -e "${RED}⚠️  .env dosyasına ANTHROPIC_API_KEY'inizi girin!${NC}"
    echo -e "   Dosya: ${SCRIPT_DIR}/.env"
    exit 1
fi

echo -e "${GREEN}✓ API Key bulundu${NC}"

# Python bağımlılıkları
# NOT: uvicorn[standard] içindeki httptools Python 3.12 ile UYUMSUZ
# Bu yüzden sadece uvicorn (standart loop) kullanıyoruz
echo ""
echo -e "${YELLOW}📦 Python bağımlılıkları yükleniyor...${NC}"
pip3 install \
    "fastapi==0.111.0" \
    "uvicorn==0.30.1" \
    "python-multipart==0.0.9" \
    "anthropic>=0.28.0" \
    "PyMuPDF==1.24.5" \
    "sqlalchemy==2.0.30" \
    "aiosqlite==0.20.0" \
    "python-dotenv==1.0.1" \
    "aiofiles==23.2.1" \
    "pydantic==2.7.1" \
    --break-system-packages -q 2>&1 | grep -E "^(ERROR|Successfully)" || true

echo -e "${GREEN}✓ Python bağımlılıkları hazır${NC}"

# Node.js / npm kontrolü
echo ""
if command -v npm &> /dev/null; then
    echo -e "${YELLOW}📦 Frontend bağımlılıkları yükleniyor...${NC}"
    cd frontend
    npm install --silent 2>/dev/null || npm install
    echo -e "${YELLOW}🔨 Frontend build ediliyor...${NC}"
    npm run build
    cd ..
    echo -e "${GREEN}✓ Frontend build hazır (dist/)${NC}"
else
    echo -e "${YELLOW}⚠️  npm bulunamadı — sadece API modu başlıyor.${NC}"
    echo -e "   Frontend için: sudo apt install nodejs npm && ./start.sh"
fi

# data klasörü
mkdir -p data

# Local IP göster
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 Sunucu başlatılıyor...${NC}"
echo -e "${GREEN}   Yerel  : http://localhost:9009${NC}"
echo -e "${GREEN}   Ağ     : http://${LOCAL_IP}:9009${NC}"
echo -e "${GREEN}   API    : http://${LOCAL_IP}:9009/docs${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Durdurmak için: ${YELLOW}Ctrl+C${NC}"
echo ""

cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 9009
