#!/bin/bash
# ─── Geliştirme Modu: Backend (9000) + Frontend dev server (5173) ─────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}🔧 Dev modu başlatılıyor...${NC}"
echo -e "   Backend  : http://${LOCAL_IP}:9009"
echo -e "   Frontend : http://${LOCAL_IP}:5173  (hot-reload)"
echo -e "   API Docs : http://${LOCAL_IP}:9009/docs"
echo ""
echo -e "   ${YELLOW}Durdurmak için: Ctrl+C${NC}"
echo ""

mkdir -p data

# Backend başlat (arka planda)
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

sleep 2

# Frontend dev server başlat
cd frontend
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

# İkisini birlikte durdur
trap "echo ''; echo 'Durduruluyor...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
