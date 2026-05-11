"""유니버스 종목 관리 API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from dantadanta.api.market import MarketApi
from web.api.database import get_session
from web.api.deps import get_market_api
from web.api.models import UniverseSymbol

router = APIRouter(prefix="/api/universe", tags=["universe"])

_OVERSEAS_MARKETS = {"NASD", "NYSE", "AMEX", "SEHK", "TKSE"}


class AddSymbolRequest(BaseModel):
    symbol: str
    market: str = "KRX"


@router.get("")
def get_universe(session: Session = Depends(get_session)):
    return session.exec(select(UniverseSymbol).order_by(UniverseSymbol.added_at)).all()


@router.post("", status_code=201)
async def add_symbol(
    req: AddSymbolRequest,
    session: Session = Depends(get_session),
    market_api: MarketApi = Depends(get_market_api),
):
    market = req.market.upper()
    symbol = req.symbol.strip().upper()

    # 국내 종목코드는 6자리 숫자로 패딩
    if market == "KRX":
        symbol = symbol.zfill(6)

    if session.get(UniverseSymbol, symbol):
        raise HTTPException(status_code=409, detail="이미 등록된 종목입니다")

    # 종목명 조회
    try:
        if market == "KRX":
            price_data = await market_api.get_price(symbol)
            name = price_data.get("hts_kor_isnm", symbol)
        else:
            price_data = await market_api.get_overseas_price(symbol, market)
            name = price_data.get("name", symbol) or price_data.get("rsym", symbol)
    except Exception:
        name = symbol

    row = UniverseSymbol(symbol=symbol, name=name, market=market)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/{symbol}/screen")
def toggle_screen(symbol: str, session: Session = Depends(get_session)):
    row = session.get(UniverseSymbol, symbol)
    if not row:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    row.screen = not row.screen
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{symbol}", status_code=204)
def delete_symbol(symbol: str, session: Session = Depends(get_session)):
    row = session.get(UniverseSymbol, symbol)
    if not row:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    session.delete(row)
    session.commit()
