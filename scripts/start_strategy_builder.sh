#!/bin/bash
# KIS Strategy Builder 서버 실행 (포트 8001)
# DantaDanta API(8000)와 충돌 방지

cd /Users/jehyunjung/Codes/open-trading-api/strategy_builder

# DantaDanta .env에서 KIS 인증 정보 주입
export $(grep -E "^KIS_APP_KEY|^KIS_APP_SECRET|^KIS_ACCOUNT_NO|^KIS_IS_MOCK" \
    /Users/jehyunjung/Codes/DantaDanta/.env | xargs)

uv run uvicorn backend.main:app --port 8001 --reload
