"""텔레그램 봇 알림 + 커맨드 처리."""

import asyncio

import httpx
from loguru import logger

from dantadanta.config import get_settings

_API_BASE = "https://api.telegram.org/bot{token}"


async def send(message: str) -> bool:
    """텔레그램으로 메시지 전송."""
    cfg = get_settings()
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        logger.info("[알림 미설정] {}", message)
        return True

    url = f"{_API_BASE.format(token=cfg.telegram_token)}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "chat_id": cfg.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            })
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("텔레그램 전송 실패: {}", exc)
        return False


async def notify_order(side: str, symbol: str, qty: int, price: int, reason: str) -> None:
    """봇 자동매매 체결 알림."""
    side_kr = "🔴 매수" if side == "buy" else "🔵 매도"
    price_str = f"{price:,}원" if price else "시장가"
    msg = (
        f"📊 <b>{side_kr} 체결</b>\n"
        f"종목: {symbol}\n"
        f"수량: {qty:,}주 / 단가: {price_str}\n"
        f"사유: {reason}"
    )
    await send(msg)


async def notify_web_order(side: str, symbol: str, name: str, qty: int, price_str: str) -> None:
    """웹/텔레그램 수동주문 알림."""
    label = "🔴 매수" if side == "매수" else "🔵 매도"
    display = name or symbol
    msg = f"{label} <b>{display}</b>({symbol})\n{qty}주 @{price_str}\n<i>수동주문</i>"
    await send(msg)


async def notify_error(context: str, error: str) -> None:
    await send(f"⚠️ <b>오류 발생</b>\n{context}\n{error}")


async def notify_summary(net_asset: int, stocks_eval: int, pnl_amount: int, holdings_count: int) -> None:
    sign = "+" if pnl_amount >= 0 else ""
    msg = (
        f"📈 <b>일간 요약</b>\n"
        f"순자산: {net_asset:,}원\n"
        f"주식평가: {stocks_eval:,}원\n"
        f"평가손익: {sign}{pnl_amount:,}원\n"
        f"보유종목: {holdings_count}개"
    )
    await send(msg)


# ── 커맨드 폴링 ──────────────────────────────────────────

_last_update_id: int = 0


async def _get_updates(token: str) -> list[dict]:
    global _last_update_id
    url = f"{_API_BASE.format(token=token)}/getUpdates"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={"offset": _last_update_id + 1, "timeout": 10})
            data = resp.json()
            updates = data.get("result", [])
            if updates:
                _last_update_id = updates[-1]["update_id"]
            return updates
    except Exception:
        return []


async def _handle_command(text: str, order_api) -> str:  # noqa: ANN001
    """커맨드별 응답 생성."""
    from dantadanta.engine import state  # 순환 임포트 방지

    parts = text.strip().split()
    cmd = parts[0].lower()

    # ── 상태 조회 ──
    if cmd == "/status":
        account = await order_api.get_account()
        cash = account.net_asset - account.stocks_eval
        sign = "+" if account.pnl_amount >= 0 else ""
        paused_str = " (일시정지 중)" if state.is_paused() else ""
        return (
            f"📊 <b>현재 상태{paused_str}</b>\n"
            f"순자산: {account.net_asset:,}원\n"
            f"가용현금: {cash:,}원\n"
            f"주식평가: {account.stocks_eval:,}원\n"
            f"평가손익: {sign}{account.pnl_amount:,}원\n"
            f"보유종목: {len(account.holdings)}개"
        )

    if cmd == "/holdings":
        account = await order_api.get_account()
        if not account.holdings:
            return "보유 종목이 없습니다."
        lines = ["💼 <b>보유 종목</b>"]
        for h in account.holdings:
            sign = "+" if h.pnl_rate >= 0 else ""
            lines.append(
                f"• {h.name}({h.symbol}) {h.qty}주\n"
                f"  평단 {h.avg_price:,.0f}원 | {sign}{h.pnl_rate:.2f}% ({sign}{h.pnl_amount:,}원)"
            )
        return "\n".join(lines)

    # ── 종목 검색: /search 이름 ──
    if cmd == "/search":
        if len(parts) < 2:
            return "사용법: /search 종목명\n예) /search 삼성\n예) /search apple"
        keyword = " ".join(parts[1:]).lower()
        try:
            from sqlmodel import Session, create_engine, select
            from web.api.models import UniverseSymbol
            engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
            with Session(engine) as session:
                rows = session.exec(select(UniverseSymbol)).all()
            matches = [
                r for r in rows
                if keyword in r.name.lower() or keyword in r.symbol.lower()
            ]
            if not matches:
                return f"🔍 '{keyword}' 검색 결과 없음\n유니버스에 등록된 종목만 검색됩니다."
            lines = [f"🔍 <b>'{keyword}' 검색 결과</b>"]
            for r in matches[:10]:
                lines.append(f"• {r.name}  <code>{r.symbol}</code>  [{r.market}]")
            return "\n".join(lines)
        except Exception as exc:
            return f"검색 오류: {exc}"

    # ── 매수: /buy SYMBOL QTY [PRICE] ──
    if cmd == "/buy":
        if len(parts) < 3:
            return "사용법: /buy 종목코드 수량 [지정가]\n예) /buy 005930 10\n예) /buy 005930 10 75000"
        symbol = parts[1].upper()
        try:
            qty = int(parts[2])
            price = int(parts[3]) if len(parts) >= 4 else 0
        except ValueError:
            return "수량·가격은 숫자로 입력하세요."

        try:
            result = await order_api.buy(symbol, qty, price)
            price_str = f"{price:,}원" if price else "시장가"
            from dantadanta.engine.order_recorder import record_order
            record_order(order_no=result.order_no, symbol=symbol, side="buy",
                         qty=qty, price=price, reason="텔레그램 수동주문")
            if price == 0:
                from dantadanta.engine.order_recorder import update_filled_price
                asyncio.create_task(update_filled_price(result.order_no, symbol, "buy", order_api))
            return f"✅ <b>매수 주문 완료</b>\n{symbol} {qty}주 @{price_str}\n주문번호: {result.order_no}"
        except Exception as exc:
            return f"❌ 매수 주문 실패\n{exc}"

    # ── 매도: /sell SYMBOL [QTY] [PRICE] ──
    if cmd == "/sell":
        if len(parts) < 2:
            return "사용법: /sell 종목코드 [수량] [지정가]\n예) /sell 005930\n예) /sell 005930 5\n예) /sell 005930 5 76000"
        symbol = parts[1].upper()
        try:
            qty_arg = int(parts[2]) if len(parts) >= 3 else None
            price = int(parts[3]) if len(parts) >= 4 else 0
        except ValueError:
            return "수량·가격은 숫자로 입력하세요."

        # 수량 미지정 시 전량 매도
        if qty_arg is None:
            account = await order_api.get_account()
            holding = next((h for h in account.holdings if h.symbol == symbol), None)
            if not holding:
                return f"{symbol} 보유 종목이 없습니다."
            qty_arg = holding.qty

        try:
            result = await order_api.sell(symbol, qty_arg, price)
            price_str = f"{price:,}원" if price else "시장가"
            from dantadanta.engine.order_recorder import record_order
            record_order(order_no=result.order_no, symbol=symbol, side="sell",
                         qty=qty_arg, price=price, reason="텔레그램 수동주문")
            if price == 0:
                from dantadanta.engine.order_recorder import update_filled_price
                asyncio.create_task(update_filled_price(result.order_no, symbol, "sell", order_api))
            return f"✅ <b>매도 주문 완료</b>\n{symbol} {qty_arg}주 @{price_str}\n주문번호: {result.order_no}"
        except Exception as exc:
            return f"❌ 매도 주문 실패\n{exc}"

    # ── 전량 매도: /sellall ──
    if cmd == "/sellall":
        account = await order_api.get_account()
        if not account.holdings:
            return "보유 종목이 없습니다."

        from dantadanta.engine.order_recorder import record_order
        lines = ["🔴 <b>전량 매도 시작</b>"]
        for h in account.holdings:
            try:
                result = await order_api.sell(h.symbol, h.qty)
                record_order(order_no=result.order_no, symbol=h.symbol, side="sell",
                             qty=h.qty, price=h.current_price, name=h.name, reason="텔레그램 전량매도")
                lines.append(f"✅ {h.name}({h.symbol}) {h.qty}주 → 주문번호 {result.order_no}")
            except Exception as exc:
                lines.append(f"❌ {h.symbol} 실패: {exc}")
        return "\n".join(lines)

    # ── 스캘핑 토글: /scalp on|off ──
    if cmd == "/scalp":
        if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
            return "사용법: /scalp on 또는 /scalp off"
        enabled = parts[1].lower() == "on"
        try:
            from sqlmodel import Session, create_engine
            from web.api.routers.config import set_config_value
            engine = create_engine("sqlite:///./dantadanta.db", connect_args={"check_same_thread": False})
            with Session(engine) as s:
                set_config_value(s, "scalping_enabled", "true" if enabled else "false")
            status = "✅ 스캘핑 활성화" if enabled else "⏸ 스캘핑 비활성화"
            return f"{status}\n손절 -0.5% / 익절 +1.0% / 최대 3종목"
        except Exception as exc:
            return f"설정 오류: {exc}"

    # ── 봇 일시정지: /stop ──
    if cmd == "/stop":
        state.set_paused(True)
        return "⏸ <b>봇 일시정지</b>\n매매 사이클 및 자동 손절·익절이 중단됩니다.\n재개하려면 /resume 을 입력하세요."

    # ── 봇 재개: /resume ──
    if cmd == "/resume":
        state.set_paused(False)
        return "▶️ <b>봇 재개</b>\n매매 사이클 및 자동 손절·익절이 재개됩니다."

    if cmd == "/help":
        return (
            "📋 <b>사용 가능한 커맨드</b>\n\n"
            "<b>조회</b>\n"
            "/status — 현재 수익률 및 계좌 요약\n"
            "/holdings — 보유 종목 목록\n"
            "/search 종목명 — 종목코드 검색\n\n"
            "<b>주문</b>\n"
            "/buy 종목코드 수량 [지정가] — 매수\n"
            "/sell 종목코드 [수량] [지정가] — 매도 (수량 생략 시 전량)\n"
            "/sellall — 전 종목 전량 매도\n\n"
            "<b>봇 제어</b>\n"
            "/stop — 자동매매 일시정지\n"
            "/resume — 자동매매 재개\n\n"
            "/help — 도움말"
        )

    return "알 수 없는 커맨드입니다. /help 를 입력하세요."


_BOT_COMMANDS = [
    ("status",   "현재 수익률 및 계좌 요약"),
    ("holdings", "보유 종목 목록"),
    ("search",   "종목코드 검색  예) /search 삼성"),
    ("scalp",    "스캘핑 on/off  예) /scalp on"),
    ("buy",      "매수  예) /buy 005930 10 [지정가]"),
    ("sell",     "매도  예) /sell 005930 [수량] [지정가]"),
    ("sellall",  "전 종목 전량 매도"),
    ("stop",     "자동매매 일시정지"),
    ("resume",   "자동매매 재개"),
    ("help",     "도움말"),
]


async def _register_commands(token: str) -> None:
    url = f"{_API_BASE.format(token=token)}/setMyCommands"
    commands = [{"command": cmd, "description": desc} for cmd, desc in _BOT_COMMANDS]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"commands": commands})
        logger.info("텔레그램 커맨드 목록 등록 완료")
    except Exception as exc:
        logger.warning("커맨드 목록 등록 실패: {}", exc)


async def command_polling_loop(order_api) -> None:  # noqa: ANN001
    """텔레그램 커맨드 폴링 루프. 봇 시작 시 백그라운드로 실행."""
    cfg = get_settings()
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        return

    await _register_commands(cfg.telegram_token)
    logger.info("텔레그램 커맨드 폴링 시작")
    while True:
        try:
            updates = await _get_updates(cfg.telegram_token)
            for update in updates:
                msg = update.get("message", {})
                text = msg.get("text", "")
                if text.startswith("/"):
                    response = await _handle_command(text, order_api)
                    await send(response)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("커맨드 폴링 오류: {}", exc)
        await asyncio.sleep(2)
