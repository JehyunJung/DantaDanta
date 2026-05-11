"""FastAPI 앱 진입점."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from dantadanta.api.rest import KisRestClient
from dantadanta.engine.price_cache import get_price_cache
from dantadanta.universe import KRX_UNIVERSE, US_UNIVERSE
from web.api import ws as ws_module
from web.api.database import get_session, init_db
from web.api.deps import set_client
from web.api.models import UniverseSymbol
from web.api.routers import account, chart, config, orders, screener, universe
from sqlmodel import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    init_db()

    # universe.py 종목을 DB에 시드 (최초 1회)
    for session in get_session():
        existing = {r.symbol for r in session.exec(select(UniverseSymbol)).all()}

        # 국내 시드
        for info in KRX_UNIVERSE:
            if info["symbol"] not in existing:
                session.add(UniverseSymbol(
                    symbol=info["symbol"], name=info["name"],
                    market=info["market"], sector=info["sector"],
                ))
        # 미국 시드
        for info in US_UNIVERSE:
            if info["symbol"] not in existing:
                session.add(UniverseSymbol(
                    symbol=info["symbol"], name=info["name"],
                    market=info["market"], sector=info["sector"],
                ))
        session.commit()

    # .env 값을 DB config 초기값으로 시드 (DB에 없을 때만)
    from dantadanta.config import get_settings
    from web.api.models import AppConfig
    from web.api.routers.config import set_config_value
    cfg = get_settings()
    for session in get_session():
        if not session.get(AppConfig, "budget_limit"):
            set_config_value(session, "budget_limit", str(cfg.budget_limit))
        if not session.get(AppConfig, "max_position_ratio"):
            set_config_value(session, "max_position_ratio", str(cfg.max_position_ratio))

    client = KisRestClient()
    await client.__aenter__()
    set_client(client)
    asyncio.create_task(ws_module.broadcast_loop())

    # 유니버스 국내 종목 실시간 가격 캐시 시작
    for session in get_session():
        all_symbols = [r.symbol for r in session.exec(select(UniverseSymbol)).all()]
    asyncio.create_task(get_price_cache().run(all_symbols))

    logger.info("DantaDanta API 서버 시작")
    yield
    # 종료
    get_price_cache().stop()
    await client.__aexit__(None, None, None)
    logger.info("DantaDanta API 서버 종료")


app = FastAPI(title="DantaDanta API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(account.router)
app.include_router(orders.router)
app.include_router(chart.router)
app.include_router(screener.router)
app.include_router(universe.router)
app.include_router(config.router)


@app.websocket("/ws/price/{symbol}")
async def price_ws(symbol: str, websocket: WebSocket):
    await ws_module.subscribe(symbol, websocket)


@app.get("/api/health")
def health():
    return {"status": "ok"}
