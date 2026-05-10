"""이동평균 골든/데드크로스 전략."""

import pandas as pd

from sagopalgo.analysis.indicators import add_indicators
from sagopalgo.strategy.base import BaseStrategy, Signal, TradeSignal


class MaCrossStrategy(BaseStrategy):
    """단기 EMA(5)가 중기 EMA(20)를 상향 돌파하면 매수, 하향 돌파하면 매도."""

    def __init__(self, fast: int = 5, slow: int = 20, rsi_oversold: float = 35.0) -> None:
        self._fast = fast
        self._slow = slow
        self._rsi_oversold = rsi_oversold

    @property
    def name(self) -> str:
        return f"MACross(EMA{self._fast}/EMA{self._slow})"

    def evaluate(self, symbol: str, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self._slow + 5:
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="데이터 부족")

        df = add_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        fast_col = f"EMA_{self._fast}"
        slow_col = f"EMA_{self._slow}"
        rsi = last.get("RSI_14")

        if fast_col not in df.columns or slow_col not in df.columns:
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="지표 계산 실패")

        golden_cross = prev[fast_col] <= prev[slow_col] and last[fast_col] > last[slow_col]
        dead_cross = prev[fast_col] >= prev[slow_col] and last[fast_col] < last[slow_col]

        if golden_cross:
            rsi_ok = rsi is None or rsi < 70  # 과매수 구간에서는 매수 자제
            if rsi_ok:
                confidence = 0.8 if (rsi and rsi < self._rsi_oversold) else 0.6
                return TradeSignal(
                    signal=Signal.BUY,
                    symbol=symbol,
                    reason=f"골든크로스 EMA{self._fast}>{self._slow} RSI={rsi:.1f}" if rsi else "골든크로스",
                    confidence=confidence,
                )

        if dead_cross:
            return TradeSignal(
                signal=Signal.SELL,
                symbol=symbol,
                reason=f"데드크로스 EMA{self._fast}<{self._slow}",
                confidence=0.8,
            )

        return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="신호 없음")
