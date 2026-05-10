"""KIS API 연결 및 기본 동작 확인 스크립트."""

import asyncio
from datetime import date, timedelta

from loguru import logger

from dantadanta.api.auth import get_token_manager
from dantadanta.api.market import MarketApi
from dantadanta.api.order import OrderApi
from dantadanta.api.rest import KisRestClient
from dantadanta.config import get_settings


async def main() -> None:
    cfg = get_settings()
    logger.info("=== KIS API 연결 테스트 ===")
    logger.info("모드: {}", "모의투자" if cfg.kis_is_mock else "실거래")
    logger.info("계좌: {}-{}", cfg.account_prefix, cfg.account_suffix)
    logger.info("Base URL: {}", cfg.kis_base_url)

    # 싱글턴 — 파일 캐시 재사용, 프로세스 내 공유
    logger.info("\n[1] 액세스 토큰 확인")
    token = await get_token_manager().get_access_token()
    logger.info("토큰 앞 20자: {}...", token[:20])

    async with KisRestClient() as client:
        market = MarketApi(client)
        order = OrderApi(client)

        logger.info("\n[2] 현재가 조회 — 삼성전자(005930)")
        price = await market.get_price("005930")
        logger.info(
            "현재가: {:,}원 / 전일대비: {}원 / 거래량: {:,}",
            int(price.get("stck_prpr", 0)),
            price.get("prdy_vrss", "N/A"),
            int(price.get("acml_vol", 0)),
        )

        logger.info("\n[3] 일봉 차트 조회 — 삼성전자 최근 5일")
        end = date.today()
        start = end - timedelta(days=10)
        df = await market.get_daily_chart("005930", start, end)
        if not df.empty:
            logger.info("조회된 봉 수: {}개", len(df))
            logger.info("\n{}", df[["date", "open", "high", "low", "close", "volume"]].tail(5).to_string(index=False))

        logger.info("\n[4] 계좌 잔고 조회")
        account = await order.get_account()
        logger.info("예수금: {:,}원", account.cash)
        logger.info("총평가: {:,}원", account.total_eval)
        logger.info("보유종목: {}개", len(account.holdings))
        for h in account.holdings:
            logger.info(
                "  - {} {} {}주 평단={:,.0f}원 손익={:+,}원({:+.2f}%)",
                h.symbol, h.name, h.qty, h.avg_price, h.pnl_amount, h.pnl_rate,
            )

    logger.info("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
