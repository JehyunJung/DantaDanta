"""KIS Strategy Builder 연동 전략.

Strategy Builder 서버(localhost:8001)의 /api/strategies/execute 를 호출해
BUY/SELL/HOLD 신호를 받아온다. 서버가 꺼져있으면 HOLD로 fallback.
"""

import httpx
import pandas as pd
from loguru import logger

from dantadanta.strategy.base import BaseStrategy, Signal, TradeSignal

_BUILDER_URL = "http://localhost:8001/api/strategies/execute"
_TIMEOUT = 5.0


class KisBuilderStrategy(BaseStrategy):
    """Strategy Builder 프리셋 전략을 사용하는 클래스."""

    def __init__(self, strategy_id: str = "golden_cross", params: dict | None = None) -> None:
        self._strategy_id = strategy_id
        self._params = params or {}

    @property
    def name(self) -> str:
        return f"KisBuilder:{self._strategy_id}"

    def evaluate(self, symbol: str, df: pd.DataFrame) -> TradeSignal:
        try:
            resp = httpx.post(
                _BUILDER_URL,
                json={
                    "strategy_id": self._strategy_id,
                    "stocks": [symbol],
                    "params": self._params,
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            for r in results:
                if r.get("code") == symbol:
                    action = r.get("action", "HOLD").upper()
                    reason = r.get("reason", "")
                    strength = float(r.get("strength", 0.5))
                    signal = Signal.BUY if action == "BUY" else Signal.SELL if action == "SELL" else Signal.HOLD
                    return TradeSignal(signal=signal, symbol=symbol, reason=reason, confidence=strength)

        except Exception as exc:
            logger.debug("Strategy Builder 연결 실패 — HOLD fallback | {}: {}", symbol, exc)

        return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="Builder 연결 불가")
