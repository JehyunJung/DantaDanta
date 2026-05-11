"""볼린저밴드 + RSI 스캘핑 전략 (분봉 기반)."""

import pandas as pd
import pandas_ta as ta

from dantadanta.strategy.base import BaseStrategy, Signal, TradeSignal


class BbRsiScalpStrategy(BaseStrategy):
    """1분봉 기준 볼린저밴드 하단 이탈 + RSI 과매도 진입 전략.

    매수: 종가 < BB 하단 AND RSI < rsi_buy
    매도: 종가 > BB 중선(20MA) OR RSI > rsi_sell
    """

    def __init__(
        self,
        bb_window: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_buy: float = 30.0,
        rsi_sell: float = 65.0,
    ) -> None:
        self._bb_window = bb_window
        self._bb_std = bb_std
        self._rsi_period = rsi_period
        self._rsi_buy = rsi_buy
        self._rsi_sell = rsi_sell

    @property
    def name(self) -> str:
        return f"BB+RSI Scalp(bb{self._bb_window}/{self._bb_std}, rsi{self._rsi_buy}/{self._rsi_sell})"

    def evaluate(self, symbol: str, df: pd.DataFrame) -> TradeSignal:
        min_rows = self._bb_window + self._rsi_period
        if len(df) < min_rows:
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="데이터 부족")

        df = df.copy()
        bb = df.ta.bbands(length=self._bb_window, std=self._bb_std)
        rsi = df.ta.rsi(length=self._rsi_period)
        if bb is None or rsi is None:
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="지표 계산 실패")

        df = pd.concat([df, bb, rsi], axis=1)
        last = df.iloc[-1]

        close = last["close"]
        bb_lower = last.get(f"BBL_{self._bb_window}_{self._bb_std}")
        bb_mid   = last.get(f"BBM_{self._bb_window}_{self._bb_std}")
        rsi_val  = last.get(f"RSI_{self._rsi_period}")

        if bb_lower is None or bb_mid is None or rsi_val is None:
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="지표 없음")

        if close < bb_lower and rsi_val < self._rsi_buy:
            return TradeSignal(
                signal=Signal.BUY,
                symbol=symbol,
                reason=f"BB하단이탈+RSI과매도 RSI={rsi_val:.1f}",
                confidence=min(1.0, (self._rsi_buy - rsi_val) / self._rsi_buy + 0.5),
            )

        if close > bb_mid or rsi_val > self._rsi_sell:
            reason = "BB중선돌파" if close > bb_mid else f"RSI과매수({rsi_val:.1f})"
            return TradeSignal(signal=Signal.SELL, symbol=symbol, reason=reason, confidence=0.8)

        return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="신호 없음")
