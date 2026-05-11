#!/bin/bash
# DantaDanta 전체 실행 스크립트

cleanup() {
    echo ""
    echo "종료 중..."
    kill $BOT_PID $API_PID $WEB_PID 2>/dev/null
    wait $BOT_PID $API_PID $WEB_PID 2>/dev/null
    echo "완료"
}
trap cleanup SIGINT SIGTERM

echo "=== DantaDanta 시작 ==="

# 트레이딩 봇
uv run python -m dantadanta &
BOT_PID=$!
echo "봇 시작 (PID: $BOT_PID)"

# FastAPI
uv run python -m uvicorn web.api.main:app --port 8000 &
API_PID=$!
echo "API 서버 시작 (PID: $API_PID)"

# Next.js
cd web/frontend && npm run dev &
WEB_PID=$!
cd ../..
echo "웹 대시보드 시작 (PID: $WEB_PID)"

echo ""
echo "대시보드: http://localhost:3000"
echo "API:      http://localhost:8000"
echo "종료:     Ctrl+C"
echo ""

wait
