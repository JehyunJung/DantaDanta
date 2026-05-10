"""SQLModel DB 테이블 정의."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class OrderRecord(SQLModel, table=True):
    """주문 체결 내역."""

    id: Optional[int] = Field(default=None, primary_key=True)
    order_no: str = Field(index=True)
    symbol: str = Field(index=True)
    name: str = ""
    side: str  # buy / sell
    qty: int
    price: int
    amount: int  # qty * price
    reason: str = ""
    strategy: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
