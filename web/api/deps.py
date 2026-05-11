"""FastAPI 의존성 주입."""

from dantadanta.api.market import MarketApi
from dantadanta.api.order import OrderApi
from dantadanta.api.rest import KisRestClient
from dantadanta.engine.price_cache import PriceCache, get_price_cache

# 앱 전체에서 하나의 클라이언트 공유
_client: KisRestClient | None = None


def get_client() -> KisRestClient:
    assert _client is not None, "클라이언트가 초기화되지 않았습니다"
    return _client


def get_market_api() -> MarketApi:
    return MarketApi(get_client())


def get_order_api() -> OrderApi:
    return OrderApi(get_client())


def set_client(client: KisRestClient) -> None:
    global _client
    _client = client


def get_cache() -> PriceCache:
    return get_price_cache()
