"""주문 체결 내역을 SQLite DB에 저장하는 헬퍼."""

import asyncio
from datetime import datetime

from loguru import logger
from sqlmodel import Session, create_engine, select

_DB_URL = "sqlite:///./dantadanta.db"
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})
    return _engine


def record_order(
    order_no: str,
    symbol: str,
    side: str,
    qty: int,
    price: float,
    name: str = "",
    reason: str = "",
    strategy: str = "",
) -> None:
    """주문 내역을 DB에 기록. 실패해도 매매 흐름에 영향 없도록 예외 흡수."""
    try:
        from web.api.models import OrderRecord
        record = OrderRecord(
            order_no=order_no,
            symbol=symbol,
            name=name,
            side=side,
            qty=qty,
            price=price,
            amount=qty * price,
            reason=reason,
            strategy=strategy,
            created_at=datetime.now(),
        )
        with Session(_get_engine()) as session:
            session.add(record)
            session.commit()
        logger.debug("주문 기록 완료 | {} {} {}주 @{:,}", side, symbol, qty, price)
    except Exception as exc:
        logger.warning("주문 기록 실패 (무시): {}", exc)


def _is_overseas_symbol(symbol: str) -> bool:
    return symbol.isalpha() and len(symbol) <= 5


async def _get_overseas_price_yf(symbol: str) -> float:
    """yfinance로 해외 종목 현재가 조회 (USD)."""
    import asyncio as _asyncio
    import yfinance as yf

    def _fetch():
        info = yf.Ticker(symbol).fast_info
        return getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None) or 0.0

    try:
        return await _asyncio.get_event_loop().run_in_executor(None, _fetch)
    except Exception:
        return 0.0


async def update_filled_price(order_no: str, symbol: str, side: str, order_api) -> None:
    """시장가 주문 체결가 업데이트 (봇/텔레그램/웹 공통).

    국내: 1차 CCLD API → 2차 잔고평균단가/PriceCache
    해외: yfinance 현재가
    """
    from dantadanta.engine.price_cache import get_price_cache

    await asyncio.sleep(2)

    filled: float = 0.0

    if _is_overseas_symbol(symbol):
        filled = await _get_overseas_price_yf(symbol)
    else:
        try:
            filled = float(await order_api.get_filled_price(order_no))
        except Exception:
            pass

        if filled <= 0:
            try:
                if side == "buy":
                    account = await order_api.get_account()
                    for h in account.holdings:
                        if h.symbol == symbol and h.avg_price > 0:
                            filled = float(h.avg_price)
                            break
                else:
                    filled = float(get_price_cache().get(symbol) or 0)
            except Exception:
                pass

    if filled > 0:
        try:
            from web.api.models import OrderRecord
            with Session(_get_engine()) as s:
                record = s.exec(
                    select(OrderRecord).where(OrderRecord.order_no == order_no)
                ).first()
                if record:
                    record.price = filled
                    record.amount = record.qty * filled
                    s.add(record)
                    s.commit()
            logger.debug("체결가 업데이트 | {} {} @{:,}", symbol, order_no, filled)
        except Exception as exc:
            logger.warning("체결가 업데이트 실패 (무시): {}", exc)
