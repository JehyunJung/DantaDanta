"""자동 매매 엔진 — 전략 신호를 받아 주문 실행."""

from datetime import date, timedelta

from loguru import logger

from dantadanta.analysis.news import get_news_sentiment
from dantadanta.api.market import MarketApi
from dantadanta.api.order import OrderApi
from dantadanta.config import get_settings
from dantadanta.engine.budget import BudgetManager
from dantadanta.engine.order_recorder import record_order
from dantadanta.notify.telegram import notify_order
from dantadanta.strategy.base import BaseStrategy, Signal

def _load_trade_config() -> dict:
    try:
        from sqlmodel import Session, create_engine
        from web.api.routers.config import get_config
        engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
        with Session(engine) as s:
            cfg = get_config(s)
        return {
            "sl_rate":               -float(cfg.get("swing_sl_rate", 5.0)) / 100,
            "tp_rate":                float(cfg.get("swing_tp_rate", 5.0)) / 100,
            "news_enabled":           cfg.get("news_enabled", "true") == "true",
            "news_threshold":         float(cfg.get("news_threshold", -0.3)),
            "krx_budget_limit":            int(cfg.get("krx_budget_limit", 10_000_000)),
            "krx_max_pos_ratio":           float(cfg.get("krx_max_position_ratio", 0.2)),
            "overseas_budget_limit":       int(cfg.get("overseas_budget_limit", 10_000_000)),
            "overseas_max_pos_ratio":      float(cfg.get("overseas_max_position_ratio", 0.2)),
            "strategy_id":                 cfg.get("strategy_id", "ma_cross"),
            "kis_builder_strategy":        cfg.get("kis_builder_strategy", "golden_cross"),
        }
    except Exception:
        return {"sl_rate": -0.05, "tp_rate": 0.05, "news_enabled": True,
                "news_threshold": -0.3, "krx_budget_limit": 10_000_000,
                "krx_max_pos_ratio": 0.2, "overseas_budget_limit": 10_000_000,
                "overseas_max_pos_ratio": 0.2, "strategy_id": "ma_cross",
                "kis_builder_strategy": "golden_cross"}


def _load_market_map() -> dict[str, str]:
    """DB에서 symbol → market 매핑 로드."""
    try:
        from sqlmodel import Session, create_engine, select
        from web.api.models import UniverseSymbol
        engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
        with Session(engine) as s:
            return {r.symbol: r.market for r in s.exec(select(UniverseSymbol)).all()}
    except Exception:
        return {}


class Trader:
    def __init__(
        self,
        market_api: MarketApi,
        order_api: OrderApi,
        budget: BudgetManager,
        strategy: BaseStrategy,
        universe: list[str],
        budget_overseas: BudgetManager | None = None,
    ) -> None:
        self._market = market_api
        self._order = order_api
        self._budget_krx = budget
        self._budget_overseas = budget_overseas or budget
        self._strategy = strategy
        self._universe = universe
        self._cfg = get_settings()

    async def run_cycle(self) -> None:
        tcfg = _load_trade_config()
        sl_rate = tcfg["sl_rate"]
        tp_rate = tcfg["tp_rate"]
        news_enabled   = tcfg["news_enabled"]
        news_threshold = tcfg["news_threshold"]

        # 전략 동적 교체
        strategy_id = tcfg.get("strategy_id", "ma_cross")
        if strategy_id == "kis_builder":
            from dantadanta.strategy.kis_builder import KisBuilderStrategy
            self._strategy = KisBuilderStrategy(strategy_id=tcfg.get("kis_builder_strategy", "golden_cross"))
        else:
            from dantadanta.strategy.ma_cross import MaCrossStrategy
            self._strategy = MaCrossStrategy()

        # 예산 설정을 config에서 동기화
        self._budget_krx.update_limits(tcfg["krx_budget_limit"], tcfg["krx_max_pos_ratio"])
        self._budget_overseas.update_limits(tcfg["overseas_budget_limit"], tcfg["overseas_max_pos_ratio"])

        logger.info("=== 매매 사이클 시작 | 전략={} | 손절={:.1f}% 익절={:.1f}% ===",
                    self._strategy.name, abs(sl_rate) * 100, tp_rate * 100)

        account = await self._order.get_account()
        cash = account.net_asset - account.stocks_eval  # 실제 가용 현금
        logger.info("계좌 현황 | 순자산={:,}원 / 주식평가={:,}원 / 가용현금={:,}원 / 보유종목={}개",
                    account.net_asset, account.stocks_eval, cash, len(account.holdings))

        # 마켓별 보유 주식 평가금액 분리
        market_map = _load_market_map()
        krx_stocks_eval = sum(
            h.current_price * h.qty for h in account.holdings
            if market_map.get(h.symbol, "KRX") == "KRX"
        )
        overseas_stocks_eval = sum(
            h.current_price * h.qty for h in account.holdings
            if market_map.get(h.symbol, "KRX") != "KRX"
        )
        overseas_cash = account.overseas_cash
        self._budget_krx.sync(cash, krx_stocks_eval)
        self._budget_overseas.sync(overseas_cash, overseas_stocks_eval)

        # 1. 보유 종목 손절/익절 체크
        for h in account.holdings:
            if h.qty <= 0:
                continue
            is_domestic_hold = market_map.get(h.symbol, "KRX") == "KRX"
            budget = self._budget_krx if is_domestic_hold else self._budget_overseas
            reason = None
            if h.pnl_rate <= sl_rate * 100:
                reason = "손절"
                logger.warning("손절 발동 | {} 수익률={:.2f}%", h.symbol, h.pnl_rate)
            elif h.pnl_rate >= tp_rate * 100:
                reason = "익절"
                logger.info("익절 발동 | {} 수익률={:.2f}%", h.symbol, h.pnl_rate)

            if reason:
                try:
                    if is_domestic_hold:
                        result = await self._order.sell(h.symbol, h.qty)
                    else:
                        excd = market_map.get(h.symbol, "NYSE")
                        result = await self._order.sell_overseas(h.symbol, excd, h.qty)
                    await budget.record_sell(h.symbol, h.current_price * h.qty)
                    record_order(order_no=result.order_no, symbol=h.symbol, side="sell",
                                 qty=h.qty, price=h.current_price, name=h.name, reason=reason)
                    await notify_order("sell", h.symbol, h.qty, h.current_price, reason)
                except Exception as exc:
                    logger.error("{} 매도 실패 | {}: {}", reason, h.symbol, exc)

        # 2. 유니버스 스캔
        held_symbols = {h.symbol for h in account.holdings}  # 이미 보유 중인 종목
        end = date.today()
        start = end - timedelta(days=120)

        for symbol in self._universe:
            market = market_map.get(symbol, "KRX")
            is_domestic = market == "KRX"

            try:
                # 차트 데이터 조회 — KRX는 시간봉 우선, 부족하면 일봉 fallback
                if is_domestic:
                    from dantadanta.engine.bar_store import load_bars, bar_count, MIN_BARS
                    if bar_count(symbol) >= MIN_BARS:
                        df = load_bars(symbol)
                        logger.debug("시간봉 사용 | {} ({}봉)", symbol, len(df))
                    else:
                        df = await self._market.get_daily_chart(symbol, start, end)
                        logger.debug("일봉 fallback | {} (시간봉 {}봉 적립 중)", symbol, bar_count(symbol))
                else:
                    df = await self._market.get_overseas_chart(symbol, market, end)

                if df.empty or len(df) < 30:
                    continue

                # 전략이 내부적으로 지표 계산
                signal = self._strategy.evaluate(symbol, df)
                if signal.signal != Signal.BUY:
                    logger.info("HOLD | {} [{}] — {}", symbol, market, signal.reason)
                    continue

                # 이미 보유 중인 종목은 재매수 안 함
                if symbol in held_symbols:
                    logger.debug("재매수 스킵 | {} 이미 보유 중", symbol)
                    continue

                # 뉴스 감성 필터 (config에서 활성화 시)
                if news_enabled:
                    news_score, _ = await get_news_sentiment(symbol, market)
                    if news_score < news_threshold:
                        logger.info("감성 필터 매수 보류 | {} score={:.2f} (기준={:.2f})",
                                    symbol, news_score, news_threshold)
                        continue

                # 현재가 조회
                if is_domestic:
                    price_data = await self._market.get_price(symbol)
                    current_price = int(price_data.get("stck_prpr", 0))
                    price_krw = current_price
                else:
                    price_data = await self._market.get_overseas_price(symbol, market)
                    current_price = float(price_data.get("last", 0))   # USD
                    price_krw = int(price_data.get("last_krw", 0))      # KRW 환산

                if current_price <= 0 or price_krw <= 0:
                    continue

                # 수량 산정 — 예산/수량은 KRW 기준
                budget = self._budget_krx if is_domestic else self._budget_overseas
                invest_amount = min(budget.per_stock_limit(), budget.remaining)
                qty = invest_amount // price_krw
                if qty <= 0:
                    continue

                amount = qty * price_krw  # KRW 기준 예산 차감
                if not await budget.can_buy(symbol, amount):
                    continue

                # 주문 — 해외는 USD 가격으로
                if is_domestic:
                    result = await self._order.buy(symbol, qty)
                else:
                    if self._cfg.kis_is_mock:
                        logger.warning("모의투자 해외주식 미지원 — {} 스킵", symbol)
                        continue
                    result = await self._order.buy_overseas(symbol, market, qty, current_price)

                await budget.record_buy(symbol, amount)
                record_order(order_no=result.order_no, symbol=symbol, side="buy",
                             qty=qty, price=current_price, reason=signal.reason,
                             strategy=self._strategy.name)
                await notify_order("buy", symbol, qty, current_price, signal.reason)
                logger.info("매수 실행 | {} [{}] {}주 @{:,} ({})",
                            symbol, market, qty, current_price, signal.reason)

            except Exception as exc:
                logger.error("사이클 오류 | {} [{}]: {}", symbol, market, exc)

        logger.info("=== 매매 사이클 완료 ===")
