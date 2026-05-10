"""SagoPalgo 엔트리포인트 — `python -m sagopalgo` 또는 `uv run python -m sagopalgo`."""

import asyncio
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from sagopalgo.api.market import MarketApi
from sagopalgo.api.order import OrderApi
from sagopalgo.api.rest import KisRestClient
from sagopalgo.config import get_settings
from sagopalgo.engine.budget import BudgetManager
from sagopalgo.engine.trader import Trader
from sagopalgo.notify.telegram import notify_error, notify_summary
from sagopalgo.strategy.ma_cross import MaCrossStrategy

# ── 매매 대상 종목 유니버스 (필요에 따라 수정) ──────────────────────────────
UNIVERSE = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "005380",  # 현대차
    "051910",  # LG화학
    "006400",  # 삼성SDI
    "035720",  # 카카오
    "207940",  # 삼성바이오로직스
    "068270",  # 셀트리온
    "105560",  # KB금융
]

_trader: Trader | None = None


async def _build_trader(client: KisRestClient) -> Trader:
    return Trader(
        market_api=MarketApi(client),
        order_api=OrderApi(client),
        budget=BudgetManager(),
        strategy=MaCrossStrategy(),
        universe=UNIVERSE,
    )


async def _trade_job(client: KisRestClient) -> None:
    global _trader
    try:
        if _trader is None:
            _trader = await _build_trader(client)
        await _trader.run_cycle()
    except Exception as exc:
        logger.error("매매 사이클 오류: {}", exc)
        await notify_error("매매 사이클", str(exc))


async def _summary_job(client: KisRestClient) -> None:
    try:
        order_api = OrderApi(client)
        account = await order_api.get_account()
        await notify_summary(account.cash, account.total_eval, len(account.holdings))
    except Exception as exc:
        logger.error("요약 알림 오류: {}", exc)


def _setup_logger() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")
    logger.add(
        "logs/sagopalgo_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        encoding="utf-8",
    )


async def main() -> None:
    _setup_logger()
    cfg = get_settings()

    mode = "모의투자" if cfg.kis_is_mock else "실거래"
    logger.info("SagoPalgo 시작 | 모드={} 예산={:,}원", mode, cfg.budget_limit)

    async with KisRestClient() as client:
        scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

        # 장 중 30분마다 매매 사이클 실행 (9:05 ~ 15:20)
        scheduler.add_job(
            _trade_job,
            "cron",
            args=[client],
            day_of_week="mon-fri",
            hour="9-15",
            minute="5,35",
            id="trade_cycle",
        )

        # 장 마감 후 일간 요약 (15:35)
        scheduler.add_job(
            _summary_job,
            "cron",
            args=[client],
            day_of_week="mon-fri",
            hour=15,
            minute=35,
            id="daily_summary",
        )

        scheduler.start()
        logger.info("스케줄러 시작 | 30분 간격 매매 사이클 (09:05~15:20, 평일)")

        try:
            await asyncio.Event().wait()  # 종료 신호까지 대기
        except (KeyboardInterrupt, SystemExit):
            logger.info("종료 신호 수신 — 스케줄러 중단")
            scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
