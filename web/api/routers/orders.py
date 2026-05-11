"""주문 내역 API."""

import asyncio
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from dantadanta.api.order import OrderApi
from dantadanta.engine.order_recorder import record_order
from web.api.database import get_session
from web.api.deps import get_order_api
from web.api.models import OrderRecord

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderRequest(BaseModel):
    symbol: str
    qty: int
    price: int = 0  # 0 = 시장가


def _lookup_name(symbol: str, session: Session) -> str:
    from web.api.models import UniverseSymbol
    row = session.get(UniverseSymbol, symbol)
    return row.name if row and row.name else ""


async def _update_filled_price(order_no: str, order_api: OrderApi) -> None:
    """시장가 주문 체결가 조회 — 2초 후 1차, 안 되면 5초 후 2차 재시도."""
    from web.api.database import engine

    for delay in (2, 5):
        await asyncio.sleep(delay)
        try:
            filled = await order_api.get_filled_price(order_no)
            if filled > 0:
                with Session(engine) as s:
                    record = s.exec(
                        select(OrderRecord).where(OrderRecord.order_no == order_no)
                    ).first()
                    if record:
                        record.price = filled
                        record.amount = record.qty * filled
                        s.add(record)
                        s.commit()
                return
        except Exception:
            pass


@router.post("/buy")
async def manual_buy(
    body: OrderRequest,
    order_api: OrderApi = Depends(get_order_api),
    session: Session = Depends(get_session),
):
    try:
        result = await order_api.buy(body.symbol.upper(), body.qty, body.price)
        record_order(order_no=result.order_no, symbol=body.symbol.upper(),
                     side="buy", qty=body.qty, price=body.price,
                     name=_lookup_name(body.symbol.upper(), session), reason="웹 수동주문")
        if body.price == 0:
            asyncio.create_task(_update_filled_price(result.order_no, order_api))
        return {"order_no": result.order_no, "status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sell")
async def manual_sell(
    body: OrderRequest,
    order_api: OrderApi = Depends(get_order_api),
    session: Session = Depends(get_session),
):
    try:
        result = await order_api.sell(body.symbol.upper(), body.qty, body.price)
        record_order(order_no=result.order_no, symbol=body.symbol.upper(),
                     side="sell", qty=body.qty, price=body.price,
                     name=_lookup_name(body.symbol.upper(), session), reason="웹 수동주문")
        if body.price == 0:
            asyncio.create_task(_update_filled_price(result.order_no, order_api))
        return {"order_no": result.order_no, "status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
