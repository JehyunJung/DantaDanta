"""SagoPalgo 엔트리포인트 — `python -m dantadanta` 또는 `uv run python -m dantadanta`."""

import asyncio
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from dantadanta.api.auth import TokenManager
from dantadanta.api.market import MarketApi
from dantadanta.api.order import OrderApi
from dantadanta.api.rest import KisRestClient
from dantadanta.config import get_settings
from dantadanta.engine.budget import BudgetManager
from dantadanta.engine.trader import Trader
from dantadanta.notify.telegram import notify_error, notify_summary
from dantadanta.strategy.ma_cross import MaCrossStrategy
from dantadanta.universe import UNIVERSE

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
        "logs/dantadanta_{time:YYYY-MM-DD}.log",
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

    auth = TokenManager()
    async with KisRestClient(auth=auth) as client:
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
