#!/bin/bash
# Oracle Cloud Ubuntu 24.04 초기 설정
# 실행: bash setup.sh

set -e

echo "=== 1. 시스템 패키지 업데이트 ==="
sudo apt update && sudo apt upgrade -y

echo "=== 2. 의존성 설치 ==="
sudo apt install -y git curl nginx certbot python3-certbot-nginx

echo "=== 3. Node.js 설치 (Next.js용) ==="
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

echo "=== 4. uv 설치 ==="
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

echo "=== 5. 프로젝트 클론 ==="
cd ~
git clone https://github.com/YOUR_USERNAME/DantaDanta.git
cd DantaDanta

echo "=== 6. .env 파일 생성 (직접 입력 필요) ==="
cp .env.example .env
echo ""
echo ">>> .env 파일을 편집하세요: nano .env"
echo ">>> 완료 후 이 스크립트를 다시 실행하거나 아래 단계를 수동으로 진행하세요."
read -p ">>> .env 편집을 완료했으면 Enter..."

echo "=== 7. Python 의존성 설치 ==="
uv sync

echo "=== 8. 프론트엔드 빌드 ==="
cd web/frontend
npm install
npm run build
cd ../..

echo "=== 9. systemd 서비스 등록 ==="
sudo cp deploy/dantadanta-bot.service /etc/systemd/system/
sudo cp deploy/dantadanta-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dantadanta-bot dantadanta-api
sudo systemctl start dantadanta-bot dantadanta-api

echo "=== 10. Next.js 서비스 등록 ==="
# pm2 대신 systemd로 관리
cat <<EOF | sudo tee /etc/systemd/system/dantadanta-web.service
[Unit]
Description=DantaDanta Next.js Frontend
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/DantaDanta/web/frontend
ExecStart=$(which node) node_modules/.bin/next start -p 3000
Restart=always
RestartSec=5

StandardOutput=journal
StandardError=journal
SyslogIdentifier=dantadanta-web

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable dantadanta-web
sudo systemctl start dantadanta-web

echo "=== 11. nginx 설정 ==="
sudo cp deploy/nginx.conf /etc/nginx/sites-available/dantadanta
sudo ln -sf /etc/nginx/sites-available/dantadanta /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=== 설정 완료 ==="
echo "서비스 상태 확인:"
echo "  sudo systemctl status dantadanta-bot"
echo "  sudo systemctl status dantadanta-api"
echo "  sudo systemctl status dantadanta-web"
echo ""
echo "SSL 설정 (도메인이 있는 경우):"
echo "  sudo certbot --nginx -d YOUR_DOMAIN"
echo ""
echo "Oracle Cloud 방화벽 포트 개방 필요:"
echo "  - 콘솔 > Networking > Security List > Ingress Rules"
echo "  - TCP 80, 443 허용"
