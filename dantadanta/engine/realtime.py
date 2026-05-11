"""WebSocket 기반 실시간 손절·익절 모니터."""

import asyncio

from loguru import logger

from dantadanta.api.order import OrderApi
from dantadanta.api.websocket import KisWebSocketClient
from dantadanta.notify.telegram import notify_order

# H0STCNT0: 국내주식 실시간 체결가
_TR_STOCK_TICK = "H0STCNT0"

# 익절/손절 기준
TAKE_PROFIT_RATE = 0.10   # +10%
STOP_LOSS_RATE   = -0.05  # -5%

# 실시간 체결 데이터 필드 인덱스 (KIS 명세 H0STCNT0)
# data 문자열: "^" 구분, [2]=현재가
_FIELD_PRICE = 2


class RealtimeMonitor:
    """보유 종목을 WebSocket으로 실시간 감시해 손절·익절을 즉시 실행."""

    def __init__(self, order_api: OrderApi, ws_client: KisWebSocketClient) -> None:
        self._order_api = order_api
        self._ws = ws_client
        # symbol → avg_price (보유 중인 종목만)
        self._positions: dict[str, float] = {}
        # 이미 매도 주문을 낸 종목 (중복 방지)
        self._exited: set[str] = set()

    async def _refresh_positions(self) -> None:
        """보유 잔고를 다시 읽어 WebSocket 구독 목록을 갱신."""
        try:
            account = await self._order_api.get_account()
        except Exception as exc:
            logger.warning("실시간 모니터: 잔고 조회 실패 — {}", exc)
            return

        current_symbols = {h.symbol for h in account.holdings}

        # 새로 생긴 포지션 구독
        for h in account.holdings:
            if h.symbol not in self._positions:
                self._ws.subscribe(_TR_STOCK_TICK, h.symbol)
                logger.info("실시간 감시 추가 | {} (평단 {:.0f}원)", h.symbol, h.avg_price)
            self._positions[h.symbol] = h.avg_price

        # 청산된 포지션 정리
        for sym in list(self._positions):
            if sym not in current_symbols:
                self._ws.unsubscribe(_TR_STOCK_TICK, sym)
                self._positions.pop(sym, None)
                self._exited.discard(sym)
                logger.info("실시간 감시 제거 | {}", sym)

    async def run(self) -> None:
        """실시간 감시 루프. __main__ 에서 백그라운드 태스크로 실행."""
        logger.info("실시간 손절·익절 모니터 시작")

        # 첫 포지션 로드
        await self._refresh_positions()

        # 잔고 갱신 태스크 (5분마다)
        asyncio.create_task(self._position_refresh_loop())

        async for msg in self._ws.stream():
            if not isinstance(msg, dict):
                continue
            tr_id = msg.get("tr_id", "")
            if tr_id != _TR_STOCK_TICK:
                continue

            symbol = msg.get("tr_key", "")
            data_str = msg.get("data", "")
            if not data_str or symbol in self._exited:
                continue

            fields = data_str.split("^")
            if len(fields) <= _FIELD_PRICE:
                continue

            try:
                current_price = int(fields[_FIELD_PRICE])
            except (ValueError, IndexError):
                continue

            avg_price = self._positions.get(symbol)
            if avg_price is None or avg_price == 0:
                continue

            rate = (current_price - avg_price) / avg_price

            from dantadanta.engine import state
            if state.is_paused():
                continue

            if rate >= TAKE_PROFIT_RATE:
                await self._exit(symbol, current_price, "익절")
            elif rate <= STOP_LOSS_RATE:
                await self._exit(symbol, current_price, "손절")

    async def _exit(self, symbol: str, price: int, reason: str) -> None:
        if symbol in self._exited:
            return
        self._exited.add(symbol)

        try:
            account = await self._order_api.get_account()
            qty = next((h.qty for h in account.holdings if h.symbol == symbol), 0)
            if qty <= 0:
                return

            result = await self._order_api.sell(symbol, qty)
            logger.info("{} | {} {}주 @{}원", reason, symbol, qty, price)
            await notify_order("sell", symbol, qty, price, reason)

            # 포지션 제거
            self._positions.pop(symbol, None)
            self._ws.unsubscribe(_TR_STOCK_TICK, symbol)
        except Exception as exc:
            logger.error("{} 주문 실패 | {} — {}", reason, symbol, exc)
            self._exited.discard(symbol)  # 재시도 허용

    async def _position_refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(300)  # 5분마다
            await self._refresh_positions()
