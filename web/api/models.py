"""SQLModel DB 테이블 정의."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class UniverseSymbol(SQLModel, table=True):
    """매매 유니버스 종목."""

    symbol: str = Field(primary_key=True)
    name: str = ""
    market: str = "KRX"   # KRX | NASD | NYSE | AMEX
    sector: str = ""
    screen: bool = True    # 스크리닝 포함 여부
    added_at: datetime = Field(default_factory=datetime.now)


class AppConfig(SQLModel, table=True):
    """앱 설정 키-값 저장소."""
    key: str = Field(primary_key=True)
    value: str = ""


class OrderRecord(SQLModel, table=True):
    """주문 체결 내역."""

    id: Optional[int] = Field(default=None, primary_key=True)
    order_no: str = Field(index=True)
    symbol: str = Field(index=True)
    name: str = ""
    side: str  # buy / sell
    qty: int
    price: float
    amount: float  # qty * price
    reason: str = ""
    strategy: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
