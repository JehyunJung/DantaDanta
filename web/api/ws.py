"""WebSocket 실시간 현재가 브로드캐스터."""

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket
from loguru import logger

from dantadanta.api.market import MarketApi
from web.api.deps import get_market_api

# symbol → 연결된 WebSocket 목록
_subscribers: dict[str, list[WebSocket]] = defaultdict(list)


async def subscribe(symbol: str, ws: WebSocket) -> None:
    """클라이언트를 특정 종목 실시간 시세에 구독 등록."""
    await ws.accept()
    _subscribers[symbol].append(ws)
    logger.info("WS 구독 | symbol={} 총={}명", symbol, len(_subscribers[symbol]))

    try:
        while True:
            await ws.receive_text()  # 클라이언트 연결 유지 (ping 처리)
    except Exception:
        pass
    finally:
        _subscribers[symbol].remove(ws)
        logger.info("WS 해제 | symbol={}", symbol)


async def broadcast_loop(interval: float = 3.0) -> None:
    """구독자가 있는 종목의 현재가를 주기적으로 브로드캐스트."""
    market_api = get_market_api()
    while True:
        for symbol, clients in list(_subscribers.items()):
            if not clients:
                continue
            try:
                price_data = await market_api.get_price(symbol)
                msg = json.dumps({
                    "symbol": symbol,
                    "price": int(price_data.get("stck_prpr", 0)),
                    "change": price_data.get("prdy_vrss", "0"),
                    "change_rate": price_data.get("prdy_ctrt", "0"),
                    "volume": int(price_data.get("acml_vol", 0)),
                })
                dead = []
                for ws in clients:
                    try:
                        await ws.send_text(msg)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    clients.remove(ws)
            except Exception as exc:
                logger.warning("브로드캐스트 오류 | {}: {}", symbol, exc)

        await asyncio.sleep(interval)
