"""FastAPI 앱 진입점."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from sagopalgo.api.rest import KisRestClient
from web.api import ws as ws_module
from web.api.database import init_db
from web.api.deps import set_client
from web.api.routers import account, chart, orders, screener


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    init_db()
    client = KisRestClient()
    await client.__aenter__()
    set_client(client)
    asyncio.create_task(ws_module.broadcast_loop())
    logger.info("SagoPalgo API 서버 시작")
    yield
    # 종료
    await client.__aexit__(None, None, None)
    logger.info("SagoPalgo API 서버 종료")


app = FastAPI(title="SagoPalgo API", lifespan=lifespan)

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


@app.websocket("/ws/price/{symbol}")
async def price_ws(symbol: str, websocket: WebSocket):
    await ws_module.subscribe(symbol, websocket)


@app.get("/api/health")
def health():
    return {"status": "ok"}
