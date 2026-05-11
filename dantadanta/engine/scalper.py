"""스캘핑 엔진 — 분봉 BB+RSI 기반 단기 매매."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time

from loguru import logger

from dantadanta.api.market import MarketApi
from dantadanta.api.order import OrderApi
from dantadanta.engine.order_recorder import record_order
from dantadanta.engine.price_cache import PriceCache
from dantadanta.strategy.bb_rsi_scalp import BbRsiScalpStrategy
from dantadanta.strategy.base import Signal

_SCAN_INTERVAL  = 60   # 스캔 주기(초)
_TOP_N          = 10   # 스크리너 상위 N개만 스캘핑 대상


def _load_scalp_config() -> dict:
    try:
        from sqlmodel import Session, create_engine
        from web.api.routers.config import get_config
        engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
        with Session(engine) as s:
            return get_config(s)
    except Exception:
        return {
            "scalping_enabled": "false",
            "scalp_sl_rate": "0.5",
            "scalp_tp_rate": "1.0",
            "scalp_max_hold": "30",
            "scalp_max_pos": "3",
            "scalp_invest": "500000",
        }

# 국내 장 시간 (KST)
_MARKET_OPEN  = time(9, 5)
_MARKET_CLOSE = time(15, 20)


@dataclass
class ScalpPosition:
    symbol: str
    name: str
    qty: int
    entry_price: float
    entry_time: datetime = field(default_factory=datetime.now)


def _is_market_open() -> bool:
    now = datetime.now().time()
    return _MARKET_OPEN <= now <= _MARKET_CLOSE


def _load_scalp_universe() -> list[dict]:
    """스크리너 상위 종목 중 KRX만 추출."""
    try:
        from sqlmodel import Session, create_engine, select
        from web.api.models import UniverseSymbol
        engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
        with Session(engine) as s:
            rows = s.exec(select(UniverseSymbol)).all()
        return [{"symbol": r.symbol, "name": r.name}
                for r in rows if r.market == "KRX" and r.screen][:_TOP_N]
    except Exception as exc:
        logger.warning("스캘핑 유니버스 로드 실패: {}", exc)
        return []


class Scalper:
    """분봉 BB+RSI 스캘핑 엔진.

    - 매 60초마다 대상 종목 분봉 조회 → 신호 판단 → 진입/청산
    - WebSocket 가격 캐시로 실시간 SL/TP 체크
    - 최대 _MAX_POSITIONS개 동시 보유
    """

    def __init__(
        self,
        market_api: MarketApi,
        order_api: OrderApi,
        price_cache: PriceCache,
    ) -> None:
        self._market = market_api
        self._order = order_api
        self._cache = price_cache
        self._strategy = BbRsiScalpStrategy()
        self._positions: dict[str, ScalpPosition] = {}
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("스캘퍼 시작 | 전략={}", self._strategy.name)

        while self._running:
            try:
                cfg = _load_scalp_config()
                enabled = cfg.get("scalping_enabled") == "true" or cfg.get("scalping_enabled") is True

                if not enabled:
                    await asyncio.sleep(_SCAN_INTERVAL)
                    continue

                sl = -float(cfg.get("scalp_sl_rate", 0.5)) / 100
                tp =  float(cfg.get("scalp_tp_rate", 1.0)) / 100
                max_hold = int(cfg.get("scalp_max_hold", 30))
                max_pos  = int(cfg.get("scalp_max_pos", 3))
                invest   = int(cfg.get("scalp_invest", 500000))

                if _is_market_open():
                    await self._check_exits(sl, tp, max_hold)
                    await self._scan_entries(max_pos, invest)
                else:
                    if self._positions:
                        logger.info("장 마감 — 스캘핑 포지션 {}개 강제 청산", len(self._positions))
                        await self._close_all("장마감")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("스캘퍼 오류: {}", exc)

            await asyncio.sleep(_SCAN_INTERVAL)

    def stop(self) -> None:
        self._running = False

    # ── 청산 체크 ────────────────────────────────────────────

    async def _check_exits(self, sl: float, tp: float, max_hold: int) -> None:
        for symbol, pos in list(self._positions.items()):
            current = self._cache.get(symbol) or 0
            if current <= 0:
                continue

            pnl_rate = (current - pos.entry_price) / pos.entry_price
            hold_min = (datetime.now() - pos.entry_time).seconds // 60

            reason = None
            if pnl_rate <= sl:
                reason = f"손절 {pnl_rate*100:.2f}%"
            elif pnl_rate >= tp:
                reason = f"익절 {pnl_rate*100:.2f}%"
            elif hold_min >= max_hold:
                reason = f"시간청산 {hold_min}분"

            if reason:
                await self._exit(symbol, pos, int(current), reason)

    async def _close_all(self, reason: str) -> None:
        for symbol, pos in list(self._positions.items()):
            current = self._cache.get(symbol) or pos.entry_price
            await self._exit(symbol, pos, int(current), reason)

    async def _exit(self, symbol: str, pos: ScalpPosition, price: int, reason: str) -> None:
        try:
            result = await self._order.sell(symbol, pos.qty, price)
            pnl = (price - pos.entry_price) * pos.qty
            logger.info("스캘핑 청산 | {} {}주 @{:,} | {} | 손익={:+,.0f}원",
                        symbol, pos.qty, price, reason, pnl)
            record_order(order_no=result.order_no, symbol=symbol, side="sell",
                         qty=pos.qty, price=price, name=pos.name,
                         reason=f"[스캘핑] {reason}", strategy=self._strategy.name)
            del self._positions[symbol]
        except Exception as exc:
            logger.error("스캘핑 청산 실패 | {}: {}", symbol, exc)

    # ── 진입 스캔 ────────────────────────────────────────────

    async def _scan_entries(self, max_pos: int, invest: int) -> None:
        if len(self._positions) >= max_pos:
            return

        universe = _load_scalp_universe()
        for item in universe:
            symbol = item["symbol"]
            if symbol in self._positions:
                continue

            try:
                df = await self._market.get_minute_chart(symbol)
                if df.empty or len(df) < 35:
                    continue

                signal = self._strategy.evaluate(symbol, df)
                if signal.signal != Signal.BUY:
                    continue

                current = self._cache.get(symbol) or 0
                if current <= 0:
                    # 캐시 미스 시 REST fallback
                    price_data = await self._market.get_price(symbol)
                    current = int(price_data.get("stck_prpr", 0))
                if current <= 0:
                    continue

                # 예수금 확인 후 진입
                account = await self._order.get_account()
                avail_cash = account.net_asset - account.stocks_eval
                use_amount = min(invest, avail_cash // (max_pos + 1))
                qty = use_amount // int(current)
                if qty <= 0:
                    continue

                result = await self._order.buy(symbol, qty)
                pos = ScalpPosition(symbol=symbol, name=item["name"],
                                    qty=qty, entry_price=current)
                self._positions[symbol] = pos
                record_order(order_no=result.order_no, symbol=symbol, side="buy",
                             qty=qty, price=int(current), name=item["name"],
                             reason=f"[스캘핑] {signal.reason}", strategy=self._strategy.name)
                logger.info("스캘핑 진입 | {} {}주 @{:,} | {}",
                            symbol, qty, current, signal.reason)

                if len(self._positions) >= max_pos:
                    break

            except Exception as exc:
                logger.error("스캘핑 진입 스캔 오류 | {}: {}", symbol, exc)
            finally:
                await asyncio.sleep(0.2)  # rate limit 방어
