"""주문 내역 API."""

import asyncio
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from dantadanta.api.order import OrderApi
from dantadanta.engine.order_recorder import record_order, update_filled_price
from dantadanta.notify.telegram import notify_web_order
from web.api.database import get_session
from web.api.deps import get_order_api
from web.api.models import OrderRecord
from web.api.routers.account import invalidate_cache

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderRequest(BaseModel):
    symbol: str
    qty: int
    price: int = 0  # 0 = 시장가


def _lookup_name(symbol: str, session: Session) -> str:
    from web.api.models import UniverseSymbol
    row = session.get(UniverseSymbol, symbol)
    return row.name if row and row.name else ""


@router.post("/buy")
async def manual_buy(
    body: OrderRequest,
    order_api: OrderApi = Depends(get_order_api),
    session: Session = Depends(get_session),
):
    try:
        sym = body.symbol.upper()
        name = _lookup_name(sym, session)
        result = await order_api.buy(sym, body.qty, body.price)
        record_order(order_no=result.order_no, symbol=sym, side="buy",
                     qty=body.qty, price=body.price, name=name, reason="웹 수동주문")
        invalidate_cache()
        price_str = f"{body.price:,}원" if body.price else "시장가"
        asyncio.create_task(notify_web_order("매수", sym, name, body.qty, price_str))
        if body.price == 0:
            asyncio.create_task(update_filled_price(result.order_no, sym, "buy", order_api))
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
        sym = body.symbol.upper()
        name = _lookup_name(sym, session)
        result = await order_api.sell(sym, body.qty, body.price)
        record_order(order_no=result.order_no, symbol=sym, side="sell",
                     qty=body.qty, price=body.price, name=name, reason="웹 수동주문")
        invalidate_cache()
        price_str = f"{body.price:,}원" if body.price else "시장가"
        asyncio.create_task(notify_web_order("매도", sym, name, body.qty, price_str))
        if body.price == 0:
            asyncio.create_task(update_filled_price(result.order_no, sym, "sell", order_api))
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
