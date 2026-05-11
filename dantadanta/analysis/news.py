"""뉴스 헤드라인 수집 + GPT-4o mini 감성 분석."""

import asyncio
import html
import json
import re
import time

import httpx
from loguru import logger

from dantadanta.config import get_settings

_NAVER_URL  = "https://finance.naver.com/item/news_news.naver"
_YAHOO_URL  = "https://feeds.finance.yahoo.com/rss/2.0/headline"
_KR_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.naver.com",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
_EN_HEADERS = {"User-Agent": "Mozilla/5.0"}
_CACHE_TTL = 1800  # 30분
_cache: dict[str, tuple[float, float, str]] = {}  # symbol → (ts, score, summary)
_cache_lock = asyncio.Lock()


async def _fetch_headlines_domestic(symbol: str) -> list[str]:
    """네이버 금융에서 국내 종목 헤드라인 수집."""
    url = f"{_NAVER_URL}?code={symbol}&page=1&category=0"
    async with httpx.AsyncClient(timeout=10, headers=_KR_HEADERS) as client:
        resp = await client.get(url)
    titles = re.findall(r'class="title">\s*<a[^>]+>([^<]+)</a>', resp.text)
    return [html.unescape(t).strip() for t in titles[:5] if t.strip()]


async def _fetch_headlines_overseas(symbol: str) -> list[str]:
    """Yahoo Finance RSS에서 해외 종목 헤드라인 수집."""
    url = f"{_YAHOO_URL}?s={symbol}&region=US&lang=en-US"
    async with httpx.AsyncClient(timeout=10, headers=_EN_HEADERS) as client:
        resp = await client.get(url)
    titles = re.findall(r"<title>(?!Yahoo Finance)([^<]{10,})</title>", resp.text)
    return [html.unescape(t).strip() for t in titles[:5] if t.strip()]


async def _fetch_headlines(symbol: str, market: str = "KRX") -> list[str]:
    if market == "KRX":
        return await _fetch_headlines_domestic(symbol)
    return await _fetch_headlines_overseas(symbol)


async def _analyze(symbol: str, headlines: list[str]) -> tuple[float, str]:
    """GPT-4o mini로 감성 점수(-1~1)와 한줄 요약 반환."""
    from openai import AsyncOpenAI

    cfg = get_settings()
    client = AsyncOpenAI(api_key=cfg.openai_api_key)

    headlines_text = "\n".join(f"- {h}" for h in headlines)
    prompt = (
        f"다음은 한국 주식 종목코드 {symbol}의 최신 뉴스 헤드라인입니다:\n"
        f"{headlines_text}\n\n"
        "위 뉴스가 주가에 미치는 영향을 평가하세요.\n"
        "반드시 아래 JSON 형식으로만 응답하세요 (설명 없이):\n"
        '{"score": 0.3, "summary": "한줄 요약"}\n\n'
        "score 기준: -1.0(매우 부정) ~ 0.0(중립) ~ 1.0(매우 긍정)"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=120,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.choices[0].message.content or ""
    data = json.loads(raw)
    score = float(data.get("score", 0.0))
    score = max(-1.0, min(1.0, score))
    summary = str(data.get("summary", ""))
    return score, summary


async def get_news_sentiment(symbol: str, market: str = "KRX") -> tuple[float, str]:
    """뉴스 감성 점수와 요약 반환. 30분 캐시 적용.

    API 키 미설정 또는 오류 시 (0.0, "") 반환.
    """
    cfg = get_settings()
    if not cfg.openai_api_key:
        return 0.0, ""

    async with _cache_lock:
        cached = _cache.get(symbol)
        if cached and (time.monotonic() - cached[0]) < _CACHE_TTL:
            return cached[1], cached[2]

    try:
        headlines = await _fetch_headlines(symbol, market)
        if not headlines:
            logger.debug("뉴스 없음 | {}", symbol)
            return 0.0, ""

        score, summary = await _analyze(symbol, headlines)
        logger.debug("뉴스 감성 | {} score={:.2f} summary={}", symbol, score, summary)

        async with _cache_lock:
            _cache[symbol] = (time.monotonic(), score, summary)

        return score, summary

    except Exception as exc:
        logger.warning("뉴스 분석 실패 | {}: {}", symbol, exc)
        return 0.0, ""
