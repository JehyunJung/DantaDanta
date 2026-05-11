"""예산 관리자 — 실제 계좌 잔고 기반 투자 한도 관리."""

import asyncio

from loguru import logger

from dantadanta.config import get_settings


class BudgetManager:
    """실제 계좌 예수금 기반 예산 관리.

    매 사이클 시작 시 sync(cash)로 실제 잔고를 주입받아
    budget_limit과 실잔고 중 작은 값을 투자 가능 상한으로 사용.
    종목당 한도는 max_position_ratio 비율로 계산.
    """

    def __init__(self) -> None:
        cfg = get_settings()
        self._limit = cfg.budget_limit
        self._max_ratio = cfg.max_position_ratio
        self._available: int = 0        # sync()로 갱신되는 실잔고 기반 가용 금액
        self._bought_this_cycle: dict[str, int] = {}  # 이번 사이클 내 매수 금액 (중복 방지)
        self._lock = asyncio.Lock()

    def update_limits(self, budget_limit: int, max_ratio: float) -> None:
        """config 변경 시 한도 갱신."""
        self._limit = budget_limit
        self._max_ratio = max_ratio

    def sync(self, cash: int, stocks_eval: int = 0) -> None:
        """사이클 시작 시 실제 잔고로 동기화.

        투자 가능 = budget_limit - 이미 보유 중인 주식평가금액.
        전체 포트폴리오가 budget_limit을 초과하지 않도록 제한.
        """
        already_invested = stocks_eval
        headroom = max(0, self._limit - already_invested)
        self._available = min(headroom, max(0, cash))
        self._bought_this_cycle.clear()
        logger.info(
            "예산 동기화 | 한도={:,} / 보유주식={:,} / 가용현금={:,} / 투자가능={:,}원",
            self._limit, already_invested, cash, self._available,
        )

    @property
    def remaining(self) -> int:
        return max(0, self._available - sum(self._bought_this_cycle.values()))

    def per_stock_limit(self) -> int:
        return int(self._limit * self._max_ratio)

    async def can_buy(self, symbol: str, amount: int) -> bool:
        async with self._lock:
            if amount > self.remaining:
                logger.warning("잔고 부족 차단 | {} {}원 요청 / 가용={:,}원", symbol, amount, self.remaining)
                return False

            already = self._bought_this_cycle.get(symbol, 0)
            if already + amount > self.per_stock_limit():
                logger.warning("종목 한도 초과 | {} 이번사이클={}원 / 종목한도={:,}원",
                               symbol, already, self.per_stock_limit())
                return False

            return True

    async def record_buy(self, symbol: str, amount: int) -> None:
        async with self._lock:
            self._bought_this_cycle[symbol] = self._bought_this_cycle.get(symbol, 0) + amount
            logger.info("매수 기록 | {} +{:,}원 / 이번사이클합계={:,}원 / 잔여={:,}원",
                        symbol, amount, sum(self._bought_this_cycle.values()), self.remaining)

    async def record_sell(self, symbol: str, amount: int) -> None:
        logger.info("매도 기록 | {} {:,}원", symbol, amount)
