"""종목 스크리너 — 유니버스에서 매수 매력도 높은 종목 추출."""

import asyncio
import time
from dataclasses import dataclass
from datetime import date, timedelta

from loguru import logger

from dantadanta.analysis.indicators import add_indicators, score
from dantadanta.analysis.news import get_news_sentiment
from dantadanta.api.market import MarketApi
from dantadanta.engine.price_cache import PriceCache

_CONCURRENCY = 1     # 동시 API 호출 수 (KIS rate limit 고려)
_OVRS_DELAY  = 0.6   # 해외 API 호출 간격 (초당 1건 제한 대응)
_CACHE_TTL   = 2100  # 캐시 유효 시간(초) — 35분 (스케줄러 30분 주기보다 여유)
_NEWS_WEIGHT = 0.2   # 뉴스 감성 가중치 (최대 ±20점)

# 시장별 캐시 분리
_cache: dict[str, list["ScreenResult"]] = {}   # "KRX" | "US" → results
_cache_ts: dict[str, float] = {}
_cache_lock = asyncio.Lock()


@dataclass
class ScreenResult:
    symbol: str
    name: str
    market: str
    score: float
    current_price: float   # 국내=원, 해외=달러
    rsi: float | None
    news_score: float = 0.0
    news_summary: str = ""


def _is_domestic(market: str) -> bool:
    return market == "KRX"


async def _screen_one(
    symbol: str,
    market: str,
    market_api: MarketApi,
    sem: asyncio.Semaphore,
    end: date,
    min_score: float,
    name: str = "",
    price_cache: PriceCache | None = None,
) -> "ScreenResult | None":
    async with sem:
        try:
            start = end - timedelta(days=120)

            if _is_domestic(market):
                df = await market_api.get_daily_chart(symbol, start, end)
            else:
                df = await market_api.get_overseas_chart(symbol, market, end)
                await asyncio.sleep(_OVRS_DELAY)

            if df.empty or len(df) < 60:
                return None

            df = add_indicators(df)
            tech_score = score(df)

            # 현재가: 캐시 우선 → REST fallback
            if _is_domestic(market):
                cached = price_cache.get(symbol) if price_cache else None
                if cached:
                    current_price = cached
                else:
                    price_data = await market_api.get_price(symbol)
                    current_price = float(price_data.get("stck_prpr", 0))
            else:
                price_data = await market_api.get_overseas_price(symbol, market)
                current_price = float(price_data.get("last", 0))

            rsi_val = df.iloc[-1].get("RSI_14")

            mkt_key = "KRX" if _is_domestic(market) else "US"
            news_score, news_summary = await get_news_sentiment(symbol, market)

            final_score = tech_score + news_score * 100 * _NEWS_WEIGHT
            if final_score < min_score:
                return None

            logger.debug("스크리닝 | {} [{}] 기술={:.1f} 뉴스={:+.2f} 최종={:.1f}",
                         symbol, market, tech_score, news_score, final_score)
            return ScreenResult(
                symbol=symbol,
                name=name or symbol,
                market=market,
                score=round(final_score, 1),
                current_price=current_price,
                rsi=float(rsi_val) if rsi_val is not None else None,
                news_score=news_score,
                news_summary=news_summary,
            )
        except Exception as exc:
            logger.warning("스크리닝 실패 | {} [{}]: {}", symbol, market, exc)
            return None


async def screen(
    symbols: list[str],
    market_api: MarketApi,
    min_score: float = 50.0,
    names: dict[str, str] | None = None,
    markets: dict[str, str] | None = None,
    price_cache: PriceCache | None = None,
) -> list[ScreenResult]:
    """종목 리스트를 스크리닝해 min_score 이상인 종목을 점수 내림차순으로 반환."""
    global _cache, _cache_ts

    # 국내/해외 구분
    market_map = markets or {}
    has_domestic = any(_is_domestic(market_map.get(s, "KRX")) for s in symbols)
    has_overseas = any(not _is_domestic(market_map.get(s, "KRX")) for s in symbols)
    cache_key = ("KRX" if has_domestic else "") + ("US" if has_overseas else "")

    async with _cache_lock:
        if _cache.get(cache_key) and (time.monotonic() - _cache_ts.get(cache_key, 0)) < _CACHE_TTL:
            logger.debug("스크리너 캐시 히트 [{}]", cache_key)
            return [r for r in _cache[cache_key] if r.score >= min_score]

        end = date.today()
        sem = asyncio.Semaphore(_CONCURRENCY)
        name_map = names or {}

        tasks = [
            _screen_one(
                sym,
                market_map.get(sym, "KRX"),
                market_api,
                sem,
                end,
                min_score,
                name_map.get(sym, ""),
                price_cache,
            )
            for sym in symbols
        ]
        raw = await asyncio.gather(*tasks)
        results = sorted(
            (r for r in raw if r is not None),
            key=lambda r: r.score,
            reverse=True,
        )

        _cache[cache_key] = results
        _cache_ts[cache_key] = time.monotonic()
        logger.info("스크리너 완료 [{}] | {}개 중 {}개 통과", cache_key, len(symbols), len(results))
        return results
