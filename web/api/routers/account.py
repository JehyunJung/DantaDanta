"""잔고 및 계좌 요약 API."""

from fastapi import APIRouter, Depends

from dantadanta.api.order import OrderApi
from web.api.deps import get_order_api

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("")
async def get_account(order_api: OrderApi = Depends(get_order_api)):
    account = await order_api.get_account()
    return {
        "net_asset": account.net_asset,
        "stocks_eval": account.stocks_eval,
        "total_purchase": account.total_purchase,
        "pnl_amount": account.pnl_amount,
        "pnl_rate": round(account.pnl_amount / account.total_purchase * 100, 2) if account.total_purchase else 0.0,
        "holdings_count": len(account.holdings),
    }


@router.get("/positions")
async def get_positions(order_api: OrderApi = Depends(get_order_api)):
    account = await order_api.get_account()
    return [
        {
            "symbol": h.symbol,
            "name": h.name,
            "qty": h.qty,
            "avg_price": h.avg_price,
            "current_price": h.current_price,
            "pnl_amount": h.pnl_amount,
            "pnl_rate": h.pnl_rate,
            "amount": h.current_price * h.qty,
        }
        for h in account.holdings
    ]
