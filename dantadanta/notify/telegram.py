"""텔레그램 봇 알림."""

import httpx
from loguru import logger

from dantadanta.config import get_settings

_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


async def send(message: str) -> bool:
    """텔레그램으로 메시지 전송. 설정 없으면 로그만 남기고 True 반환."""
    cfg = get_settings()
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        logger.info("[알림 미설정] {}", message)
        return True

    url = _API_BASE.format(token=cfg.telegram_token)
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
    side_kr = "매수" if side == "buy" else "매도"
    msg = (
        f"📊 <b>{side_kr} 체결</b>\n"
        f"종목: {symbol}\n"
        f"수량: {qty:,}주 / 단가: {price:,}원\n"
        f"사유: {reason}"
    )
    await send(msg)


async def notify_error(context: str, error: str) -> None:
    msg = f"⚠️ <b>오류 발생</b>\n{context}\n{error}"
    await send(msg)


async def notify_summary(cash: int, total_eval: int, holdings_count: int) -> None:
    msg = (
        f"📈 <b>일간 요약</b>\n"
        f"예수금: {cash:,}원\n"
        f"총평가: {total_eval:,}원\n"
        f"보유종목: {holdings_count}개"
    )
    await send(msg)
