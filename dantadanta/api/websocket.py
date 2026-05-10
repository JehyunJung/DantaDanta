"""KIS WebSocket 실시간 시세 클라이언트."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import websockets
from loguru import logger

from dantadanta.api.auth import TokenManager
from dantadanta.config import Settings, get_settings

_RECONNECT_DELAY = 5  # 재연결 대기(초)
_MAX_RECONNECT = 10


class KisWebSocketClient:
    """KIS 실시간 시세 WebSocket 클라이언트.

    사용법:
        client = KisWebSocketClient()
        await client.subscribe("H0STCNT0", "005930")  # 삼성전자 체결가
        async for msg in client.stream():
            print(msg)
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._cfg = settings or get_settings()
        self._auth = TokenManager(self._cfg)
        self._subscriptions: list[tuple[str, str]] = []  # (tr_id, tr_key)
        self._ws: Any = None
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._running = False

    def subscribe(self, tr_id: str, tr_key: str) -> None:
        """구독 항목 추가. connect() 전에 호출하거나 연결 중에도 가능."""
        self._subscriptions.append((tr_id, tr_key))

    def unsubscribe(self, tr_id: str, tr_key: str) -> None:
        self._subscriptions = [s for s in self._subscriptions if s != (tr_id, tr_key)]

    async def stream(self) -> AsyncIterator[dict]:
        """수신 메시지를 비동기 이터레이터로 반환."""
        self._running = True
        asyncio.create_task(self._connect_loop())
        while self._running:
            yield await self._queue.get()

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _connect_loop(self) -> None:
        for attempt in range(_MAX_RECONNECT):
            try:
                approval_key = await self._auth.get_ws_approval_key()
                async with websockets.connect(self._cfg.kis_ws_url) as ws:
                    self._ws = ws
                    logger.info("WebSocket 연결 성공 (시도 {})", attempt + 1)
                    await self._send_subscriptions(ws, approval_key)
                    await self._receive_loop(ws)
            except Exception as exc:
                logger.warning("WebSocket 연결 끊김: {} — {}초 후 재시도", exc, _RECONNECT_DELAY)
                self._auth.invalidate()
                await asyncio.sleep(_RECONNECT_DELAY)

        logger.error("WebSocket 최대 재시도({}) 초과 — 스트리밍 중단", _MAX_RECONNECT)
        self._running = False

    async def _receive_loop(self, ws: Any) -> None:
        async for raw in ws:
            msg = self._parse(raw)
            if msg:
                await self._queue.put(msg)

    async def _send_subscriptions(self, ws: Any, approval_key: str) -> None:
        for tr_id, tr_key in self._subscriptions:
            payload = _build_subscribe_payload(approval_key, tr_id, tr_key)
            await ws.send(json.dumps(payload))
            logger.debug("구독 전송 | tr_id={} tr_key={}", tr_id, tr_key)

    @staticmethod
    def _parse(raw: str | bytes) -> dict | None:
        """KIS WebSocket 응답 파싱. 시세 데이터가 아닌 메시지는 None 반환."""
        if isinstance(raw, bytes):
            raw = raw.decode()

        # 제어 메시지(JSON)
        if raw.startswith("{"):
            data = json.loads(raw)
            if data.get("header", {}).get("tr_id") == "PINGPONG":
                return None  # 하트비트 무시
            return data

        # 시세 데이터 ("|" 구분 플랫 문자열)
        parts = raw.split("|")
        if len(parts) < 4:
            return None
        return {"tr_id": parts[1], "tr_key": parts[2], "data": parts[3]}


def _build_subscribe_payload(approval_key: str, tr_id: str, tr_key: str) -> dict:
    return {
        "header": {
            "approval_key": approval_key,
            "custtype": "P",
            "tr_type": "1",  # 1=등록, 2=해제
            "content-type": "utf-8",
        },
        "body": {
            "input": {
                "tr_id": tr_id,
                "tr_key": tr_key,
            }
        },
    }
