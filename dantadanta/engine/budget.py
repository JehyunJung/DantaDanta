"""예산 관리자 — 투자 한도 초과 방지."""

import asyncio

from loguru import logger

from dantadanta.config import get_settings


class BudgetManager:
    """설정된 예산 한도 내에서만 매수를 허용.

    - 총 투자금액(매수 체결액 합산)이 budget_limit을 넘으면 차단
    - 종목당 투자 비율(max_position_ratio)도 함께 체크
    """

    def __init__(self) -> None:
        cfg = get_settings()
        self._limit = cfg.budget_limit
        self._max_ratio = cfg.max_position_ratio
        self._invested: dict[str, int] = {}  # symbol → 투자금액
        self._lock = asyncio.Lock()

    @property
    def total_invested(self) -> int:
        return sum(self._invested.values())

    @property
    def remaining(self) -> int:
        return max(0, self._limit - self.total_invested)

    def per_stock_limit(self) -> int:
        return int(self._limit * self._max_ratio)

    async def can_buy(self, symbol: str, amount: int) -> bool:
        """매수 가능 여부 확인. amount = 매수 예정 금액(원)."""
        async with self._lock:
            if self.total_invested + amount > self._limit:
                logger.warning(
                    "예산 초과 차단 | {} {}원 요청 / 잔여예산={}원",
                    symbol, amount, self.remaining,
                )
                return False

            symbol_invested = self._invested.get(symbol, 0)
            if symbol_invested + amount > self.per_stock_limit():
                logger.warning(
                    "종목 한도 초과 차단 | {} 현재투자={}원 / 종목한도={}원",
                    symbol, symbol_invested, self.per_stock_limit(),
                )
                return False

            return True

    async def record_buy(self, symbol: str, amount: int) -> None:
        async with self._lock:
            self._invested[symbol] = self._invested.get(symbol, 0) + amount
            logger.info(
                "매수 기록 | {} +{}원 / 총투자={}원 / 잔여={}원",
                symbol, amount, self.total_invested, self.remaining,
            )

    async def record_sell(self, symbol: str, amount: int) -> None:
        async with self._lock:
            current = self._invested.get(symbol, 0)
            self._invested[symbol] = max(0, current - amount)
            logger.info("매도 기록 | {} -{}원", symbol, amount)
