"""종목 스크리너 — 유니버스에서 매수 매력도 높은 종목 추출."""

from dataclasses import dataclass
from datetime import date, timedelta

from loguru import logger

from sagopalgo.analysis.indicators import add_indicators, score
from sagopalgo.api.market import MarketApi


@dataclass
class ScreenResult:
    symbol: str
    name: str
    score: float
    current_price: int
    rsi: float | None


async def screen(
    symbols: list[str],
    market_api: MarketApi,
    min_score: float = 50.0,
) -> list[ScreenResult]:
    """종목 리스트를 스크리닝해 min_score 이상인 종목을 점수 내림차순으로 반환."""
    results: list[ScreenResult] = []
    end = date.today()
    start = end - timedelta(days=120)  # 지표 계산에 충분한 기간

    for symbol in symbols:
        try:
            df = await market_api.get_daily_chart(symbol, start, end)
            if df.empty or len(df) < 60:
                continue

            df = add_indicators(df)
            s = score(df)
            if s < min_score:
                continue

            price_data = await market_api.get_price(symbol)
            current_price = int(price_data.get("stck_prpr", 0))
            name = price_data.get("hts_kor_isnm", symbol)
            rsi = df.iloc[-1].get("RSI_14")

            results.append(ScreenResult(
                symbol=symbol,
                name=name,
                score=s,
                current_price=current_price,
                rsi=float(rsi) if rsi is not None else None,
            ))
            logger.debug("스크리닝 | {} {} 점={:.1f}", symbol, name, s)

        except Exception as exc:
            logger.warning("스크리닝 실패 | {}: {}", symbol, exc)

    return sorted(results, key=lambda r: r.score, reverse=True)
