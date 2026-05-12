"""DantaDanta 엔트리포인트 — `python -m dantadanta` 또는 `uv run python -m dantadanta`."""

import asyncio
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from dantadanta.api.auth import TokenManager
from dantadanta.api.market import MarketApi
from dantadanta.api.order import OrderApi
from dantadanta.api.rest import KisRestClient
from dantadanta.api.websocket import KisWebSocketClient
from dantadanta.config import get_settings
from dantadanta.engine.budget import BudgetManager
from dantadanta.engine.trader import Trader
from dantadanta.engine.scalper import Scalper
from dantadanta.engine.realtime import RealtimeMonitor
from dantadanta.engine.price_cache import get_price_cache
from dantadanta.notify.telegram import command_polling_loop, notify_error, notify_summary
from dantadanta.strategy.ma_cross import MaCrossStrategy

_krx_trader: Trader | None = None
_us_trader: Trader | None = None


def _load_universe(market: str | None = None) -> list[str]:
    """market="KRX" → 국내, market="US" → 해외(NASD/NYSE), None → 전체."""
    try:
        from sqlmodel import Session, create_engine, select
        from web.api.models import UniverseSymbol
        engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
        with Session(engine) as s:
            rows = s.exec(select(UniverseSymbol)).all()
            if rows:
                if market == "KRX":
                    return [r.symbol for r in rows if r.market == "KRX"]
                if market == "US":
                    return [r.symbol for r in rows if r.market != "KRX"]
                return [r.symbol for r in rows]
    except Exception:
        pass
    from dantadanta.universe import UNIVERSE
    return UNIVERSE


async def _build_trader(client: KisRestClient, market: str | None = None) -> Trader:
    return Trader(
        market_api=MarketApi(client),
        order_api=OrderApi(client),
        budget=BudgetManager(),
        strategy=MaCrossStrategy(),
        universe=_load_universe(market),
        budget_overseas=BudgetManager(),
    )


async def _krx_trade_job(client: KisRestClient) -> None:
    from dantadanta.engine import state
    if state.is_paused():
        logger.info("봇 일시정지 중 — 국장 사이클 건너뜀")
        return

    global _krx_trader
    try:
        if _krx_trader is None:
            _krx_trader = await _build_trader(client, market="KRX")
        await _krx_trader.run_cycle()
    except Exception as exc:
        logger.error("국장 사이클 오류: {}", exc)
        await notify_error("국장 매매 사이클", str(exc))


def _is_us_market_open() -> bool:
    """서머타임 자동 반영 — America/New_York 기준 09:30~16:00 평일."""
    from zoneinfo import ZoneInfo
    from datetime import datetime, time
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:
        return False
    return time(9, 30) <= now_et.time() < time(16, 0)


async def _us_trade_job(client: KisRestClient) -> None:
    if get_settings().kis_is_mock:
        return
    if not _is_us_market_open():
        return

    from dantadanta.engine import state
    if state.is_paused():
        logger.info("봇 일시정지 중 — 미장 사이클 건너뜀")
        return

    global _us_trader
    try:
        if _us_trader is None:
            _us_trader = await _build_trader(client, market="US")
        await _us_trader.run_cycle()
    except Exception as exc:
        logger.error("미장 사이클 오류: {}", exc)
        await notify_error("미장 매매 사이클", str(exc))


async def _collect_bars_job(client: KisRestClient) -> None:
    """매 15분마다 KRX 분봉 수집 → 시간봉 적재."""
    market_api = MarketApi(client)
    symbols = _load_universe(market="KRX")
    added = 0
    for symbol in symbols:
        try:
            n = await market_api.collect_hourly_bars(symbol)
            added += n
        except Exception:
            pass
    if added:
        logger.info("시간봉 적재 완료 | {}개 봉 추가", added)


async def _screen_job(client: KisRestClient, market: str) -> None:
    """스크리너 캐시 프리워밍 — 웹 페이지가 항상 캐시를 히트하도록."""
    if market != "KRX" and get_settings().kis_is_mock:
        return
    try:
        from sqlmodel import Session, create_engine, select
        from web.api.models import UniverseSymbol
        from dantadanta.analysis.screener import screen

        engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
        with Session(engine) as s:
            rows = s.exec(select(UniverseSymbol).where(UniverseSymbol.screen == True)).all()  # noqa: E712

        if market == "KRX":
            rows = [r for r in rows if r.market == "KRX"]
        else:
            rows = [r for r in rows if r.market != "KRX"]

        symbols = [r.symbol for r in rows]
        names   = {r.symbol: r.name   for r in rows}
        markets = {r.symbol: r.market for r in rows}

        market_api = MarketApi(client)
        logger.info("스크리너 프리워밍 시작 [{}] | {}개 종목", market, len(symbols))
        await screen(symbols, market_api, min_score=0.0, names=names, markets=markets)
        logger.info("스크리너 프리워밍 완료 [{}]", market)
    except Exception as exc:
        logger.error("스크리너 프리워밍 오류 [{}]: {}", market, exc)


async def _summary_job(client: KisRestClient) -> None:
    try:
        order_api = OrderApi(client)
        account = await order_api.get_account()
        await notify_summary(account.net_asset, account.stocks_eval, account.pnl_amount, len(account.holdings))
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
    logger.info("DantaDanta 시작 | 모드={} 예산={:,}원", mode, cfg.budget_limit)

    # yfinance로 KRX 시간봉 즉시 워밍업 (부족한 종목만)
    from dantadanta.engine.bar_store import warmup_from_yfinance
    _warmup_symbols = _load_universe(market="KRX")
    logger.info("시간봉 워밍업 시작 | KRX {}개 종목", len(_warmup_symbols))
    for _sym in _warmup_symbols:
        warmup_from_yfinance(_sym, market="KRX")
    logger.info("시간봉 워밍업 완료")

    auth = TokenManager()
    async with KisRestClient(auth=auth) as client:
        scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

        # 국장 15분마다 매매 사이클 (KST 09:05~15:20, 평일)
        scheduler.add_job(
            _krx_trade_job,
            "cron",
            args=[client],
            day_of_week="mon-fri",
            hour="9-15",
            minute="5,20,35,50",
            id="krx_trade_cycle",
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

        # 미국장 15분마다 매매 사이클 — 서머타임(22:30~05:00) + 표준시(23:30~06:00) 모두 커버
        # _is_us_market_open()이 내부에서 실제 개장 여부 필터링
        scheduler.add_job(
            _us_trade_job,
            "cron",
            args=[client],
            day_of_week="mon-fri",
            hour="22,23,0,1,2,3,4,5,6",
            minute="5,20,35,50",
            id="us_trade_cycle",
        )

        # KRX 시간봉 수집 (매매 사이클과 동일 시간)
        scheduler.add_job(
            _collect_bars_job, "cron", args=[client],
            day_of_week="mon-fri", hour="9-15", minute="5,20,35,50",
            id="bar_collect",
        )

        # 국장 스크리너 프리워밍 — 장전 2회(08:30, 08:50) + 장중 30분 간격(09:00~15:00)
        scheduler.add_job(
            _screen_job, "cron", args=[client, "KRX"],
            day_of_week="mon-fri", hour="8",  minute="30,50", id="krx_screen_pre",
        )
        scheduler.add_job(
            _screen_job, "cron", args=[client, "KRX"],
            day_of_week="mon-fri", hour="9-15", minute="0,30", id="krx_screen",
        )

        # 미장 스크리너 — 서머타임/표준시 모두 커버 (21:30~06:30 KST)
        scheduler.add_job(
            _screen_job, "cron", args=[client, "US"],
            day_of_week="mon-fri", hour="21,22,23,0,1,2,3,4,5,6", minute="0,30", id="us_screen",
        )

        scheduler.start()
        logger.info("스케줄러 시작 | 국장 15분 간격 (09:05~15:20) / 미장 15분 간격 (서머타임 22:35~04:50 / 표준시 23:35~05:50)")

        order_api = OrderApi(client)
        market_api = MarketApi(client)
        price_cache = get_price_cache()

        # 텔레그램 커맨드 폴링 (백그라운드)
        tg_task = asyncio.create_task(command_polling_loop(order_api))

        # 실시간 손절·익절 모니터 (백그라운드)
        ws_client = KisWebSocketClient()
        monitor = RealtimeMonitor(order_api=order_api, ws_client=ws_client)
        rt_task = asyncio.create_task(monitor.run())

        # 스캘퍼 (백그라운드)
        scalper = Scalper(market_api=market_api, order_api=order_api, price_cache=price_cache)
        scalp_task = asyncio.create_task(scalper.run())
        logger.info("스캘퍼 시작 | BB+RSI 분봉 전략")

        try:
            await asyncio.Event().wait()  # 종료 신호까지 대기
        except (KeyboardInterrupt, SystemExit):
            logger.info("종료 신호 수신 — 스케줄러 중단")
            scheduler.shutdown()
            scalper.stop()
            tg_task.cancel()
            rt_task.cancel()
            scalp_task.cancel()
            await asyncio.gather(tg_task, rt_task, scalp_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
