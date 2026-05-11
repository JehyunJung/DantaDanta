"""잔고 및 계좌 요약 API."""

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Depends

from dantadanta.api.order import OrderApi
from web.api.deps import get_order_api

router = APIRouter(prefix="/api/account", tags=["account"])

_CACHE_TTL = 60  # 초
_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_KIS_TIMEOUT = 5.0  # KIS API 타임아웃


async def _fetch_account(order_api: OrderApi) -> dict:
    global _cache, _cache_ts
    now = time.monotonic()

    if _cache and now - _cache_ts < _CACHE_TTL:
        return _cache

    try:
        account = await asyncio.wait_for(order_api.get_account(), timeout=_KIS_TIMEOUT)
        _cache = {
            "net_asset": account.net_asset,
            "stocks_eval": account.stocks_eval,
            "total_purchase": account.total_purchase,
            "pnl_amount": account.pnl_amount,
            "pnl_rate": round(account.pnl_amount / account.total_purchase * 100, 2) if account.total_purchase else 0.0,
            "holdings_count": len(account.holdings),
            "holdings": account.holdings,
        }
        _cache_ts = now
    except (asyncio.TimeoutError, Exception):
        pass  # 캐시 있으면 그대로, 없으면 아래서 빈 값 반환

    return _cache


@router.get("")
async def get_account(order_api: OrderApi = Depends(get_order_api)):
    data = await _fetch_account(order_api)
    if not data:
        return {
            "net_asset": 0, "stocks_eval": 0, "total_purchase": 0,
            "pnl_amount": 0, "pnl_rate": 0.0, "holdings_count": 0,
        }
    return {k: v for k, v in data.items() if k != "holdings"}


@router.get("/positions")
async def get_positions(order_api: OrderApi = Depends(get_order_api)):
    data = await _fetch_account(order_api)
    holdings = data.get("holdings", [])
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
        for h in holdings
    ]
