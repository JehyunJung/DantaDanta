# DantaDanta (단타단타)

KIS(한국투자증권) Open API 기반 자동 주식 트레이딩 시스템. 국내/미국 주식 자동 매매, 실시간 웹 대시보드, 텔레그램 알림을 제공한다.

---

## 주요 기능

- **자동 매매** — EMA 골든크로스 + MACD + RSI 필터 기반 15분 주기 매매
- **국장/미장 분리** — KRX(09:05~15:20), 미국(23:05~05:50) 별도 사이클
- **스캘핑** — BB+RSI 기반 1분봉 단기 전략 (옵션)
- **뉴스 감성 분석** — Claude API로 매수 전 뉴스 감성 필터링
- **실시간 대시보드** — Next.js 웹 UI (차트, 보유종목, 주문내역, 스크리너)
- **텔레그램 봇** — 매수/매도/조회/설정 커맨드 지원
- **실시간 손절·익절** — WebSocket 기반 실시간 가격 모니터링

---

## 시스템 구성

```
DantaDanta/
├── dantadanta/              # 트레이딩 봇 코어
│   ├── api/                 # KIS REST + WebSocket 클라이언트
│   │   ├── auth.py          # 토큰 발급/캐시 (1분 rate limit 대응)
│   │   ├── market.py        # 시세/차트 조회 (국내/해외)
│   │   ├── order.py         # 주문 실행 및 계좌 조회
│   │   ├── rest.py          # HTTP 클라이언트 (rate limit 방어)
│   │   └── websocket.py     # 실시간 체결가 구독
│   ├── analysis/
│   │   ├── screener.py      # 유니버스 종목 스코어링
│   │   ├── indicators.py    # 기술적 지표 계산
│   │   └── news.py          # 뉴스 감성 분석 (Claude API)
│   ├── engine/
│   │   ├── trader.py        # 메인 매매 사이클
│   │   ├── scalper.py       # 스캘핑 엔진 (60초 루프)
│   │   ├── budget.py        # 예산 관리 (실잔고 기반)
│   │   ├── realtime.py      # 실시간 손절·익절 모니터
│   │   ├── price_cache.py   # 실시간 가격 캐시
│   │   └── order_recorder.py# 주문 DB 기록
│   ├── strategy/
│   │   ├── ma_cross.py      # EMA(3/10) + MACD + RSI 전략
│   │   └── bb_rsi_scalp.py  # BB + RSI 스캘핑 전략
│   ├── notify/
│   │   └── telegram.py      # 텔레그램 알림 + 커맨드 폴링
│   ├── universe.py          # 국내/미국 종목 유니버스 (각 40종목)
│   └── __main__.py          # 진입점 + APScheduler 설정
│
├── web/
│   ├── api/                 # FastAPI 백엔드
│   │   ├── main.py          # 앱 진입점 + lifespan
│   │   ├── models.py        # SQLModel DB 모델
│   │   ├── routers/         # REST 엔드포인트
│   │   │   ├── account.py   # 계좌/보유종목
│   │   │   ├── chart.py     # 일봉/분봉 차트
│   │   │   ├── orders.py    # 주문 내역
│   │   │   ├── screener.py  # 종목 스크리닝
│   │   │   ├── universe.py  # 유니버스 관리
│   │   │   └── config.py    # 설정 CRUD
│   │   └── ws.py            # WebSocket 가격 브로드캐스트
│   └── frontend/            # Next.js 대시보드
│       └── src/app/
│           ├── page.tsx         # 대시보드 (잔고/수익)
│           ├── positions/       # 보유 종목
│           ├── chart/           # 캔들차트 + 지표
│           ├── orders/          # 주문 내역
│           ├── screener/        # 종목 스크리너
│           ├── universe/        # 종목 관리
│           └── config/          # 설정 페이지
│
├── run.sh                   # 봇 + API + 프론트 일괄 실행
├── pyproject.toml
└── .env.example
```

---

## 매매 전략

### 스윙 전략 (기본, 15분 주기)

| 조건 | 내용 |
|------|------|
| 매수 | EMA(3) 골든크로스 + RSI 30~65 + MACD 양전환 |
| 매도 | EMA(3) 데드크로스 또는 RSI > 75 |
| 손절 | 설정값 (기본 -3%) |
| 익절 | 설정값 (기본 +7%) |

### 스캘핑 전략 (옵션, 60초 루프)

| 조건 | 내용 |
|------|------|
| 매수 | 종가 < BB 하단 AND RSI < 30 |
| 매도 | 종가 > BB 중심선 OR RSI > 65 |

---

## 스케줄

| 사이클 | 시간 (KST) | 대상 |
|--------|-----------|------|
| 국장 매매 | 평일 09:05 - 15:20, 매 15분 | KRX 종목 |
| 미장 매매 | 평일 23:05 - 05:50, 매 15분 | NASD/NYSE 종목 |
| 일간 요약 | 평일 15:35 | 텔레그램 알림 |

---

## 설치 및 실행

### 요구사항

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- Node.js 18+
- 한국투자증권 Open API 앱키 ([발급](https://apiportal.koreainvestment.com))

### 설치

```bash
# Python 의존성
uv sync

# 프론트엔드 의존성
cd web/frontend && npm install && cd ../..

# 환경 변수 설정
cp .env.example .env
# .env 열어서 API 키 입력
```

### 환경 변수

```env
# KIS API (필수)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=12345678-01
KIS_IS_MOCK=true              # 모의투자: true / 실거래: false

# Anthropic (뉴스 감성 분석, 선택)
ANTHROPIC_API_KEY=your_key

# 텔레그램 알림 (선택)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 예산 초기값 (DB에 저장된 후엔 웹 UI에서 변경)
BUDGET_LIMIT=1000000
MAX_POSITION_RATIO=0.2
```

### 실행

```bash
# 전체 실행 (봇 + API + 프론트)
./run.sh

# 개별 실행
uv run python -m dantadanta          # 트레이딩 봇
uv run uvicorn web.api.main:app --port 8000  # API 서버
cd web/frontend && npm run dev        # 프론트엔드
```

대시보드: `http://localhost:3000`  
API: `http://localhost:8000`

---

## 웹 대시보드

| 페이지 | 내용 |
|--------|------|
| 대시보드 | 예수금, 총평가, 수익률, 최근 주문 |
| 보유 종목 | 수익률 바차트, 포트폴리오 비중, 상세 테이블 |
| 차트 | 일봉/분봉 캔들차트 + EMA/BB/RSI 지표 |
| 주문내역 | 전체 주문 기록 (자동/수동 통합) |
| 스크리너 | 유니버스 종목 스코어 실시간 조회 |
| 종목관리 | 유니버스 종목 추가/삭제/스크리닝 활성화 |
| 설정 | 예산, 손절/익절, 뉴스 필터, 스캘핑 옵션 |

---

## 텔레그램 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/status` | 현재 계좌 요약 및 수익률 |
| `/holdings` | 보유 종목 목록 |
| `/search 종목명` | 종목코드 검색 |
| `/buy 종목코드 수량 [지정가]` | 수동 매수 |
| `/sell 종목코드 [수량] [지정가]` | 수동 매도 |
| `/sellall` | 전 종목 전량 매도 |
| `/scalp on\|off` | 스캘핑 활성화/비활성화 |
| `/stop` | 자동매매 일시정지 |
| `/resume` | 자동매매 재개 |

---

## 외부 접속 (Tailscale)

포트포워딩 없이 외부에서 안전하게 접속하려면 [Tailscale](https://tailscale.com) 사용을 권장한다.

1. 서버 맥과 접속 기기에 Tailscale 설치 후 같은 계정 로그인
2. `tailscale ip` 로 서버 IP 확인
3. `http://<tailscale-ip>:3000` 으로 접속

---

## 주의사항

- **모의투자 모드**(`KIS_IS_MOCK=true`)로 충분히 검증 후 실거래 전환
- KIS 모의투자 서버는 해외 주식 API를 지원하지 않음 (해외 시세는 실서버로 자동 우회)
- 토큰 발급은 분당 1회 제한 (자동 대기 후 재시도)
- `.env` 파일은 절대 커밋하지 말 것

---

## 기술 스택

| 영역 | 스택 |
|------|------|
| 봇 코어 | Python 3.12, httpx, websockets, APScheduler |
| 지표 분석 | pandas, pandas-ta |
| AI | Anthropic Claude API (뉴스 감성) |
| 백엔드 | FastAPI, SQLModel, SQLite |
| 프론트엔드 | Next.js 15, Tailwind CSS, lightweight-charts |
| 알림 | Telegram Bot API |
