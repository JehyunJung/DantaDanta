"""WebSocket 기반 실시간 현재가 캐시.

유니버스 전체를 H0STCNT0 으로 구독해 최신 체결가를 메모리에 유지한다.
스크리너가 REST get_price() 대신 이 캐시를 읽으면 KIS API 호출이 0이 된다.
"""

import asyncio

from loguru import logger

from dantadanta.api.auth import TokenManager
from dantadanta.api.websocket import KisWebSocketClient

# H0STCNT0 데이터 필드 인덱스 (^로 구분)
_F_PRICE = 2   # 주식현재가

# KIS WebSocket 1 커넥션당 구독 가능 종목 수
_MAX_PER_CONN = 40

_TR_TICK = "H0STCNT0"


class PriceCache:
    """실시간 체결가 캐시 싱글턴."""

    def __init__(self) -> None:
        self._prices: dict[str, float] = {}
        self._running = False

    def get(self, symbol: str) -> float | None:
        return self._prices.get(symbol)

    def all(self) -> dict[str, float]:
        return dict(self._prices)

    async def run(self, symbols: list[str]) -> None:
        """백그라운드 태스크. 연결이 끊기면 자동 재시도."""
        domestic = [s for s in symbols if s.isdigit()]
        if not domestic:
            return

        self._running = True
        logger.info("가격 캐시 시작 | {}개 종목 구독", len(domestic))

        # 40개 초과 시 청크로 분할해 여러 커넥션 생성
        chunks = [domestic[i:i + _MAX_PER_CONN] for i in range(0, len(domestic), _MAX_PER_CONN)]
        tasks = [asyncio.create_task(self._stream_chunk(chunk)) for chunk in chunks]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _stream_chunk(self, symbols: list[str]) -> None:
        ws = KisWebSocketClient()
        for sym in symbols:
            ws.subscribe(_TR_TICK, sym)

        try:
            async for msg in ws.stream():
                if not self._running:
                    await ws.stop()
                    break
                if not isinstance(msg, dict):
                    continue
                if msg.get("tr_id") != _TR_TICK:
                    continue
                symbol = msg.get("tr_key", "")
                data_str = msg.get("data", "")
                if not data_str or not symbol:
                    continue
                fields = data_str.split("^")
                if len(fields) > _F_PRICE:
                    try:
                        self._prices[symbol] = float(fields[_F_PRICE])
                    except ValueError:
                        pass
        except asyncio.CancelledError:
            await ws.stop()

    def stop(self) -> None:
        self._running = False


# 프로세스 싱글턴
_cache = PriceCache()


def get_price_cache() -> PriceCache:
    return _cache
