"""Claude API 기반 뉴스 감성 분석."""

from dataclasses import dataclass

import anthropic
from loguru import logger

from sagopalgo.config import get_settings
from sagopalgo.news.collector import NewsItem

_MODEL = "claude-haiku-4-5-20251001"  # 빠르고 저렴한 모델로 감성 분석

_SYSTEM_PROMPT = """당신은 한국 주식 시장 뉴스를 분석하는 전문가입니다.
주어진 뉴스 제목들을 읽고 시장 또는 해당 종목에 대한 전반적인 감성을 분석하세요.

응답은 반드시 다음 JSON 형식으로만 답하세요:
{
  "sentiment": "positive" | "negative" | "neutral",
  "score": -1.0 ~ 1.0,
  "reason": "한 줄 요약"
}"""


@dataclass
class SentimentResult:
    sentiment: str   # positive / negative / neutral
    score: float     # -1.0 ~ 1.0
    reason: str
    news_count: int


async def analyze(news_items: list[NewsItem], symbol: str = "") -> SentimentResult:
    """뉴스 목록을 Claude로 감성 분석."""
    if not news_items:
        return SentimentResult(sentiment="neutral", score=0.0, reason="뉴스 없음", news_count=0)

    cfg = get_settings()
    if not cfg.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY 미설정 — 감성 분석 생략")
        return SentimentResult(sentiment="neutral", score=0.0, reason="API 키 없음", news_count=0)

    titles = "\n".join(f"- {item.title}" for item in news_items)
    subject = f"종목 {symbol}" if symbol else "시장 전반"
    user_msg = f"{subject} 관련 최신 뉴스 제목들:\n{titles}"

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=256,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        import json
        parsed = json.loads(raw)
        result = SentimentResult(
            sentiment=parsed.get("sentiment", "neutral"),
            score=float(parsed.get("score", 0.0)),
            reason=parsed.get("reason", ""),
            news_count=len(news_items),
        )
        logger.info(
            "감성 분석 완료 | {} sentiment={} score={:.2f}",
            subject, result.sentiment, result.score,
        )
        return result

    except Exception as exc:
        logger.warning("감성 분석 실패 | {}: {}", symbol, exc)
        return SentimentResult(sentiment="neutral", score=0.0, reason=str(exc), news_count=0)
