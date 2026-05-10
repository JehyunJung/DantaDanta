"""자동 매매 엔진 — 전략 신호를 받아 주문 실행."""

from datetime import date, timedelta

from loguru import logger

from sagopalgo.api.market import MarketApi
from sagopalgo.api.order import OrderApi
from sagopalgo.analysis.indicators import add_indicators
from sagopalgo.engine.budget import BudgetManager
from sagopalgo.news.collector import fetch_stock_news
from sagopalgo.news.sentiment import analyze as analyze_sentiment
from sagopalgo.strategy.base import BaseStrategy, Signal

_STOP_LOSS_RATE = -0.05    # -5% 손절
_TAKE_PROFIT_RATE = 0.10   # +10% 익절


class Trader:
    """매매 엔진.

    매 사이클마다:
    1. 보유 종목 손절/익절 체크
    2. 유니버스 스캔 → 전략 신호 → 감성 필터 → 주문
    """

    def __init__(
        self,
        market_api: MarketApi,
        order_api: OrderApi,
        budget: BudgetManager,
        strategy: BaseStrategy,
        universe: list[str],
    ) -> None:
        self._market = market_api
        self._order = order_api
        self._budget = budget
        self._strategy = strategy
        self._universe = universe

    async def run_cycle(self) -> None:
        """단일 매매 사이클 실행."""
        logger.info("=== 매매 사이클 시작 | 전략={} ===", self._strategy.name)

        account = await self._order.get_account()
        logger.info(
            "계좌 현황 | 예수금={:,}원 / 총평가={:,}원 / 보유종목={}개",
            account.cash, account.total_eval, len(account.holdings),
        )

        # 1. 보유 종목 손절/익절 체크
        for holding in account.holdings:
            if holding.qty <= 0:
                continue
            if holding.pnl_rate <= _STOP_LOSS_RATE * 100:
                logger.warning("손절 발동 | {} 수익률={:.2f}%", holding.symbol, holding.pnl_rate)
                await self._order.sell(holding.symbol, holding.qty)
                await self._budget.record_sell(
                    holding.symbol, holding.current_price * holding.qty
                )
            elif holding.pnl_rate >= _TAKE_PROFIT_RATE * 100:
                logger.info("익절 발동 | {} 수익률={:.2f}%", holding.symbol, holding.pnl_rate)
                await self._order.sell(holding.symbol, holding.qty)
                await self._budget.record_sell(
                    holding.symbol, holding.current_price * holding.qty
                )

        # 2. 유니버스 스캔 → 매수 신호 종목 탐색
        end = date.today()
        start = end - timedelta(days=120)

        for symbol in self._universe:
            try:
                df = await self._market.get_daily_chart(symbol, start, end)
                if df.empty or len(df) < 30:
                    continue

                df = add_indicators(df)
                signal = self._strategy.evaluate(symbol, df)

                if signal.signal != Signal.BUY:
                    continue

                # 감성 필터: 뉴스가 부정적이면 매수 보류
                news = await fetch_stock_news(symbol, max_items=5)
                sentiment = await analyze_sentiment(news, symbol)
                if sentiment.score < -0.3:
                    logger.info(
                        "감성 필터 매수 보류 | {} score={:.2f} reason={}",
                        symbol, sentiment.score, sentiment.reason,
                    )
                    continue

                # 매수 수량/금액 산정
                price_data = await self._market.get_price(symbol)
                current_price = int(price_data.get("stck_prpr", 0))
                if current_price <= 0:
                    continue

                invest_amount = min(
                    self._budget.per_stock_limit(),
                    self._budget.remaining,
                )
                qty = invest_amount // current_price
                if qty <= 0:
                    continue

                amount = qty * current_price
                if not await self._budget.can_buy(symbol, amount):
                    continue

                await self._order.buy(symbol, qty)
                await self._budget.record_buy(symbol, amount)
                logger.info(
                    "매수 실행 | {} {}주 @{:,}원 ({})",
                    symbol, qty, current_price, signal.reason,
                )

            except Exception as exc:
                logger.error("사이클 오류 | {}: {}", symbol, exc)

        logger.info("=== 매매 사이클 완료 ===")
