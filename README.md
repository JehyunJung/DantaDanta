# SagoPalgo (사고팔고)

한국투자증권(KIS) Open API 기반 자동 주식 트레이딩 시스템

## 주요 기능

- **자동 매매** — 설정한 예산 내에서 조건 기반 자동 매수/매도
- **차트 분석** — 이동평균, RSI, MACD 등 기술적 지표 기반 종목 추천
- **뉴스 감성 분석** — Claude API를 활용한 뉴스 기반 시장 조사

## 요구사항

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- 한국투자증권 Open API 앱키 ([발급 링크](https://apiportal.koreainvestment.com))

## 설치

```bash
# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력
```

## 실행

```bash
# 모의투자 모드 (기본값)
uv run python -m sagopalgo

# 실거래 모드 (.env에서 KIS_IS_MOCK=false 설정)
uv run python -m sagopalgo
```

## 프로젝트 구조

```
sagopalgo/
├── api/        # KIS API 클라이언트 (REST + WebSocket)
├── analysis/   # 차트 분석 및 기술적 지표
├── news/       # 뉴스 수집 및 감성 분석
├── strategy/   # 매매 전략 (플러그인 구조)
├── engine/     # 자동 매매 엔진 및 예산 관리
├── notify/     # 알림 모듈 (텔레그램)
└── config.py   # 설정 관리
```

## 문서

- [요구사항 초안](docs/draft/요구사항_초안_2026_05_10.md)
- [실행 플랜](docs/plans/실행플랜_v1_2026_05_10.md)
- [작업 기록](docs/workflow/작업기록_2026_05_10.md)

## 주의사항

- **모의투자 모드**로 먼저 충분히 검증 후 실거래 전환
- 예산 초과 주문은 시스템 레벨에서 차단됨
- 모든 주문 및 판단 이유는 로그에 기록됨
