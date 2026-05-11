"""EMA 크로스 + MACD 확인 + RSI 필터 전략."""

import pandas as pd
import pandas_ta as ta

from dantadanta.strategy.base import BaseStrategy, Signal, TradeSignal


class MaCrossStrategy(BaseStrategy):
    """EMA(fast)가 EMA(slow)를 골든크로스 + MACD 양전환 + RSI 필터.

    매수 조건 (모두 충족):
      1. EMA(fast)가 EMA(slow)를 상향 돌파 (골든크로스)
      2. MACD 히스토그램이 음→양 전환 (추세 확인)
      3. RSI 30~65 구간 (과매도 반등 or 중립 — 과매수 제외)

    매도 조건 (하나라도):
      - EMA(fast)가 EMA(slow)를 하향 돌파 (데드크로스)
      - RSI > 75 (과매수 과열)
    """

    def __init__(
        self,
        fast: int = 3,
        slow: int = 10,
        rsi_low: float = 30.0,
        rsi_high: float = 65.0,
    ) -> None:
        self._fast = fast
        self._slow = slow
        self._rsi_low = rsi_low
        self._rsi_high = rsi_high

    @property
    def name(self) -> str:
        return f"EMA({self._fast}/{self._slow})+MACD+RSI"

    def evaluate(self, symbol: str, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self._slow + 15:
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="데이터 부족")

        df = df.copy()

        # EMA
        df[f"EMA_{self._fast}"] = ta.ema(df["close"], length=self._fast)
        df[f"EMA_{self._slow}"] = ta.ema(df["close"], length=self._slow)

        # MACD (12/26/9)
        macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd_df is not None:
            df = pd.concat([df, macd_df], axis=1)

        # RSI
        df["RSI"] = ta.rsi(df["close"], length=14)

        df = df.dropna().reset_index(drop=True)
        if len(df) < 2:
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="지표 계산 실패")

        last = df.iloc[-1]
        prev = df.iloc[-2]

        fast_col = f"EMA_{self._fast}"
        slow_col = f"EMA_{self._slow}"
        hist_col = "MACDh_12_26_9"

        ema_fast_last = last.get(fast_col)
        ema_slow_last = last.get(slow_col)
        ema_fast_prev = prev.get(fast_col)
        ema_slow_prev = prev.get(slow_col)
        rsi = last.get("RSI")
        hist_last = last.get(hist_col)
        hist_prev = prev.get(hist_col)

        if any(v is None for v in [ema_fast_last, ema_slow_last, ema_fast_prev, ema_slow_prev]):
            return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="지표 없음")

        golden_cross = ema_fast_prev <= ema_slow_prev and ema_fast_last > ema_slow_last
        dead_cross   = ema_fast_prev >= ema_slow_prev and ema_fast_last < ema_slow_last

        # ── 매수 판단 ──────────────────────────────────────────
        if golden_cross:
            # RSI 필터: 과매도~중립 구간만 허용
            rsi_ok = rsi is None or (self._rsi_low <= rsi <= self._rsi_high)
            if not rsi_ok:
                return TradeSignal(signal=Signal.HOLD, symbol=symbol,
                                   reason=f"RSI 범위 밖 ({rsi:.1f})" if rsi else "RSI 없음")

            # MACD 확인: 음→양 전환 / 양수 / 방향이 상승 중이면 모두 OK
            macd_turning = (hist_prev is not None and hist_last is not None
                            and hist_prev < 0 and hist_last >= 0)
            macd_rising = (hist_prev is not None and hist_last is not None
                           and hist_last > hist_prev)
            macd_positive = hist_last is not None and hist_last > 0

            if hist_last is not None and not macd_rising and not macd_positive:
                # 히스토그램이 음수이면서 하락 중이면 매수 보류
                return TradeSignal(signal=Signal.HOLD, symbol=symbol,
                                   reason=f"MACD 하락 중 ({hist_last:.3f})")

            confidence = 0.9 if macd_turning else (0.8 if macd_positive else 0.65)
            rsi_str = f" RSI={rsi:.0f}" if rsi else ""
            macd_str = " MACD↑" if macd_turning else (" MACD+" if macd_positive else " MACD↗")
            return TradeSignal(
                signal=Signal.BUY,
                symbol=symbol,
                reason=f"골든크로스{macd_str}{rsi_str}",
                confidence=confidence,
            )

        # ── 매도 판단 ──────────────────────────────────────────
        if dead_cross:
            return TradeSignal(signal=Signal.SELL, symbol=symbol,
                               reason="데드크로스", confidence=0.85)

        if rsi is not None and rsi > 75:
            return TradeSignal(signal=Signal.SELL, symbol=symbol,
                               reason=f"RSI 과매수({rsi:.0f})", confidence=0.75)

        return TradeSignal(signal=Signal.HOLD, symbol=symbol, reason="신호 없음")
