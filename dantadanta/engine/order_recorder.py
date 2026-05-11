"""주문 체결 내역을 SQLite DB에 저장하는 헬퍼."""

from datetime import datetime

from loguru import logger
from sqlmodel import Session, create_engine

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
    price: int,
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
