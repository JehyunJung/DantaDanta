"""스크리너 API."""

from fastapi import APIRouter, Depends

from dantadanta.analysis.screener import screen
from dantadanta.api.market import MarketApi
from dantadanta.universe import UNIVERSE
from web.api.deps import get_market_api

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("")
async def get_screener(
    min_score: float = 0.0,
    market_api: MarketApi = Depends(get_market_api),
):
    results = await screen(UNIVERSE, market_api, min_score=min_score)
    return [
        {
            "symbol": r.symbol,
            "name": r.name,
            "score": r.score,
            "current_price": r.current_price,
            "rsi": r.rsi,
        }
        for r in results
    ]
