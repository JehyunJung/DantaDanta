"""차트 데이터 API."""

from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from dantadanta.analysis.indicators import add_indicators
from dantadanta.api.market import MarketApi
from web.api.deps import get_market_api

router = APIRouter(prefix="/api/chart", tags=["chart"])

# 분봉 리샘플 단위
_MINUTE_RESAMPLE = {"1": "1min", "5": "5min", "15": "15min", "30": "30min", "60": "60min"}

# 기간별 조회 일수 (KIS API는 D/W/M 만 지원; Y는 월봉 리샘플로 처리)
_PERIOD_DAYS = {"D": 120, "W": 730, "M": 3650, "Y": 3650}


async def _build_minute_df(symbol: str, minutes: str, market_api: MarketApi) -> pd.DataFrame:
    """분봉 데이터 조회 및 리샘플."""
    df = await market_api.get_minute_chart(symbol)
    if df.empty:
        return df

    today_str = date.today().strftime("%Y%m%d")
    df["datetime"] = pd.to_datetime(
        today_str + df["time"].str.zfill(6), format="%Y%m%d%H%M%S"
    )
    df = df.sort_values("datetime")

    if minutes != "1":
        rule = _MINUTE_RESAMPLE[minutes]
        df = df.set_index("datetime").resample(rule).agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        ).dropna().reset_index()

    # lightweight-charts는 intraday에 Unix 타임스탬프(초) 필요
    df["ts"] = df["datetime"].astype("int64") // 10**9
    return df


def _resample_yearly(df: pd.DataFrame) -> pd.DataFrame:
    """월봉 DataFrame을 연봉으로 리샘플."""
    df = df.set_index("date")
    yearly = df.resample("YE").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).dropna().reset_index()
    yearly = yearly.rename(columns={"date": "date"})
    # YE anchor는 연말(12-31)이므로 그대로 사용
    return yearly


@router.get("/{symbol}")
async def get_chart(
    symbol: str,
    period: str = Query("D", pattern=r"^([DWMY]|[1-9][05]?)$"),
    days: int = Query(120, ge=10, le=3650),
    market: str = Query("KRX"),
    market_api: MarketApi = Depends(get_market_api),
):
    # ── 분봉 처리 ──────────────────────────────────────────
    if period in _MINUTE_RESAMPLE:
        try:
            df = await _build_minute_df(symbol, period, market_api)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if df.empty:
            return {"symbol": symbol, "candles": [], "indicators": {}}

        candles = [
            {
                "time": int(row["ts"]),
                "open": int(row["open"]),
                "high": int(row["high"]),
                "low":  int(row["low"]),
                "close": int(row["close"]),
                "volume": int(row["volume"]),
            }
            for _, row in df.iterrows()
        ]
        return {"symbol": symbol, "candles": candles, "indicators": {}}

    # ── 일/주/월/연봉 처리 ───────────────────────────────────
    kis_period = "M" if period == "Y" else period
    actual_days = max(days, _PERIOD_DAYS.get(period, days))
    end = date.today()
    start = end - timedelta(days=actual_days)

    try:
        if market == "KRX":
            df = await market_api.get_daily_chart(symbol, start, end, period=kis_period)
        else:
            df = await market_api.get_overseas_chart(symbol, market, end, period=kis_period)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if df.empty:
        return {"symbol": symbol, "candles": [], "indicators": {}}

    if period == "Y":
        df = _resample_yearly(df)

    # 지표는 일봉/주봉에만 의미 있음 (데이터 포인트 충분할 때)
    if period in ("D", "W") and len(df) >= 20:
        df = add_indicators(df)

    def fmt_time(row_date) -> str:
        return row_date.strftime("%Y-%m-%d")

    candles = [
        {
            "time": fmt_time(row["date"]),
            "open":   int(row["open"]),
            "high":   int(row["high"]),
            "low":    int(row["low"]),
            "close":  int(row["close"]),
            "volume": int(row["volume"]),
        }
        for _, row in df.iterrows()
    ]

    def series(col: str) -> list:
        if col not in df.columns:
            return []
        return [
            {"time": fmt_time(row["date"]), "value": round(float(row[col]), 2)}
            for _, row in df.iterrows()
            if row[col] == row[col]  # NaN 제외
        ]

    indicators = {}
    if period in ("D", "W"):
        indicators = {
            "ema5":     series("EMA_5"),
            "ema20":    series("EMA_20"),
            "ema60":    series("EMA_60"),
            "bb_upper": series("BBU_20_2.0"),
            "bb_lower": series("BBL_20_2.0"),
            "rsi":      series("RSI_14"),
        }

    return {"symbol": symbol, "candles": candles, "indicators": indicators}
