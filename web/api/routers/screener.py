"""스크리너 API."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from dantadanta.analysis.screener import screen
from dantadanta.api.market import MarketApi
from dantadanta.engine.price_cache import PriceCache
from web.api.database import get_session
from web.api.deps import get_cache, get_market_api
from web.api.models import UniverseSymbol

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("")
async def get_screener(
    min_score: float = 0.0,
    market: str = Query("ALL"),   # ALL | KRX | NASD | NYSE | AMEX
    market_api: MarketApi = Depends(get_market_api),
    session: Session = Depends(get_session),
    price_cache: PriceCache = Depends(get_cache),
):
    rows = session.exec(
        select(UniverseSymbol).where(UniverseSymbol.screen == True)  # noqa: E712
    ).all()

    if market != "ALL":
        rows = [r for r in rows if r.market == market]

    symbols  = [r.symbol for r in rows]
    names    = {r.symbol: r.name   for r in rows}
    markets  = {r.symbol: r.market for r in rows}

    results = await screen(symbols, market_api, min_score=min_score, names=names, markets=markets, price_cache=price_cache)
    return [
        {
            "symbol":       r.symbol,
            "name":         r.name,
            "market":       r.market,
            "score":        r.score,
            "current_price": r.current_price,
            "rsi":          r.rsi,
            "news_score":   r.news_score,
            "news_summary": r.news_summary,
        }
        for r in results
    ]
