"""네이버 금융 RSS 기반 뉴스 수집."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx
from loguru import logger

_NAVER_STOCK_RSS = "https://finance.naver.com/item/news_news.naver?code={symbol}&page=1&sm=title_entity_id.basic"
_NAVER_RSS_URL = "https://finance.naver.com/news/news_rss.naver?sectionId=101"


@dataclass
class NewsItem:
    title: str
    description: str
    link: str
    pub_date: str


async def fetch_market_news(max_items: int = 20) -> list[NewsItem]:
    """네이버 금융 시장 전체 뉴스 RSS 수집."""
    return await _fetch_rss(_NAVER_RSS_URL, max_items)


async def fetch_stock_news(symbol: str, max_items: int = 10) -> list[NewsItem]:
    """특정 종목 뉴스 페이지에서 제목 수집 (RSS 미지원 → HTML 파싱)."""
    url = f"https://finance.naver.com/item/news_news.naver?code={symbol}"
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=10,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        # 간단한 텍스트 파싱 (정규식 없이 분리)
        items: list[NewsItem] = []
        text = resp.text
        # <a class="tit" ...>제목</a> 패턴 추출
        marker = 'class="tit"'
        pos = 0
        while len(items) < max_items:
            idx = text.find(marker, pos)
            if idx == -1:
                break
            start = text.find(">", idx) + 1
            end = text.find("</a>", start)
            title = text[start:end].strip()
            if title:
                items.append(NewsItem(title=title, description="", link=url, pub_date=""))
            pos = end

        logger.debug("종목 뉴스 수집 | symbol={} count={}", symbol, len(items))
        return items

    except Exception as exc:
        logger.warning("종목 뉴스 수집 실패 | {}: {}", symbol, exc)
        return []


async def _fetch_rss(url: str, max_items: int) -> list[NewsItem]:
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=10,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        channel = root.find("channel")
        if channel is None:
            return []

        items: list[NewsItem] = []
        for item in channel.findall("item")[:max_items]:
            items.append(NewsItem(
                title=_text(item, "title"),
                description=_text(item, "description"),
                link=_text(item, "link"),
                pub_date=_text(item, "pubDate"),
            ))
        return items

    except Exception as exc:
        logger.warning("RSS 수집 실패 | {}: {}", url, exc)
        return []


def _text(el: ET.Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""
