"""차트 데이터 API."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from dantadanta.analysis.indicators import add_indicators
from dantadanta.api.market import MarketApi
from web.api.deps import get_market_api

router = APIRouter(prefix="/api/chart", tags=["chart"])


@router.get("/{symbol}")
async def get_chart(
    symbol: str,
    period: str = Query("D", pattern="^[DWMY]$"),
    days: int = Query(120, ge=10, le=365),
    market_api: MarketApi = Depends(get_market_api),
):
    end = date.today()
    start = end - timedelta(days=days)
    df = await market_api.get_daily_chart(symbol, start, end, period=period)
    if df.empty:
        return {"candles": [], "indicators": {}}

    df = add_indicators(df)

    candles = [
        {
            "time": row["date"].strftime("%Y-%m-%d"),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
        }
        for _, row in df.iterrows()
    ]

    def series(col: str) -> list:
        if col not in df.columns:
            return []
        return [
            {"time": row["date"].strftime("%Y-%m-%d"), "value": round(float(row[col]), 2)}
            for _, row in df.iterrows()
            if row[col] == row[col]  # NaN 제외
        ]

    return {
        "symbol": symbol,
        "candles": candles,
        "indicators": {
            "ema5": series("EMA_5"),
            "ema20": series("EMA_20"),
            "ema60": series("EMA_60"),
            "bb_upper": series("BBU_20_2.0"),
            "bb_lower": series("BBL_20_2.0"),
            "rsi": series("RSI_14"),
        },
    }
