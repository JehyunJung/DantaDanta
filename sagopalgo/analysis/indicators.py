"""기술적 지표 계산 (pandas-ta 기반)."""

import pandas as pd
import pandas_ta as ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV DataFrame에 기술적 지표 컬럼을 추가해 반환."""
    df = df.copy()

    df.ta.ema(length=5, append=True)    # EMA_5
    df.ta.ema(length=20, append=True)   # EMA_20
    df.ta.ema(length=60, append=True)   # EMA_60

    df.ta.rsi(length=14, append=True)   # RSI_14

    macd = df.ta.macd(fast=12, slow=26, signal=9)
    if macd is not None:
        df = pd.concat([df, macd], axis=1)  # MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9

    bbands = df.ta.bbands(length=20, std=2)
    if bbands is not None:
        df = pd.concat([df, bbands], axis=1)  # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0

    return df


def score(df: pd.DataFrame) -> float:
    """마지막 행 기준으로 0~100 점수 반환. 점수가 높을수록 매수 매력도 높음."""
    if df.empty or len(df) < 2:
        return 0.0

    last = df.iloc[-1]
    prev = df.iloc[-2]
    points = 0.0

    # EMA 정배열 (단기 > 중기 > 장기)
    ema5 = last.get("EMA_5")
    ema20 = last.get("EMA_20")
    ema60 = last.get("EMA_60")
    if ema5 and ema20 and ema60:
        if ema5 > ema20 > ema60:
            points += 30

    # RSI 과매도 구간 (30 이하) → 반등 기대
    rsi = last.get("RSI_14")
    if rsi is not None:
        if rsi < 30:
            points += 25
        elif rsi < 50:
            points += 10

    # MACD 골든크로스 (MACD가 시그널 상향 돌파)
    macd_col = "MACD_12_26_9"
    sig_col = "MACDs_12_26_9"
    if macd_col in df.columns and sig_col in df.columns:
        if prev[macd_col] < prev[sig_col] and last[macd_col] > last[sig_col]:
            points += 25

    # 볼린저밴드 하단 터치 (저점 매수 시그널)
    bbl = last.get("BBL_20_2.0")
    if bbl and last["close"] <= bbl:
        points += 20

    return min(points, 100.0)
