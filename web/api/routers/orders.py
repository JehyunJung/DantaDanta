"""주문 내역 API."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from web.api.database import get_session
from web.api.models import OrderRecord

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
def get_orders(
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    stmt = select(OrderRecord).order_by(OrderRecord.created_at.desc()).limit(limit)
    records = session.exec(stmt).all()

    result = [
        {
            "id": r.id,
            "order_no": r.order_no,
            "symbol": r.symbol,
            "name": r.name,
            "side": r.side,
            "qty": r.qty,
            "price": r.price,
            "amount": r.amount,
            "reason": r.reason,
            "strategy": r.strategy,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
        if (symbol is None or r.symbol == symbol)
        and (side is None or r.side == side)
        and (start is None or r.created_at.date() >= start)
        and (end is None or r.created_at.date() <= end)
    ]
    return result
