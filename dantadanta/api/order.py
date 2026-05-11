"""KIS 주문 및 계좌 조회 API."""

from dataclasses import dataclass

from loguru import logger

from dantadanta.api.rest import KisRestClient
from dantadanta.config import get_settings

_ORDER_PATH       = "/uapi/domestic-stock/v1/trading/order-cash"
_BALANCE_PATH     = "/uapi/domestic-stock/v1/trading/inquire-balance"
_BUYABLE_PATH     = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
_OVRS_ORDER_PATH  = "/uapi/overseas-stock/v1/trading/order"
_CCLD_PATH        = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"

_TR = {
    "buy_real": "TTTC0012U",
    "buy_mock": "VTTC0012U",
    "sell_real": "TTTC0011U",
    "sell_mock": "VTTC0011U",
    "balance_real": "TTTC8434R",
    "balance_mock": "VTTC8434R",
    "buyable_real": "TTTC8908R",
    "buyable_mock": "VTTC8908R",
    "ovrs_buy_real":  "TTTT1002U",
    "ovrs_buy_mock":  "VTTT1002U",
    "ovrs_sell_real": "TTTT1006U",
    "ovrs_sell_mock": "VTTT1006U",
    "ccld_real": "TTTC8001R",
    "ccld_mock": "VTTC8001R",
}


@dataclass
class OrderResult:
    order_no: str
    symbol: str
    side: str   # buy / sell
    qty: int
    price: int


@dataclass
class HoldingItem:
    symbol: str
    name: str
    qty: int
    avg_price: float
    current_price: int
    pnl_amount: int
    pnl_rate: float


@dataclass
class AccountSummary:
    net_asset: int          # 순자산 (tot_evlu_amt)
    stocks_eval: int        # 주식평가금액 (scts_evlu_amt)
    total_purchase: int     # 총매수금액 (pchs_amt_smtl_amt)
    pnl_amount: int         # 평가손익 (evlu_pfls_smtl_amt)
    holdings: list[HoldingItem]


class OrderApi:
    def __init__(self, client: KisRestClient) -> None:
        self._c = client
        self._cfg = get_settings()

    def _tr(self, key: str) -> str:
        suffix = "mock" if self._cfg.kis_is_mock else "real"
        return _TR[f"{key}_{suffix}"]

    async def buy(self, symbol: str, qty: int, price: int = 0) -> OrderResult:
        """시장가(price=0) 또는 지정가 매수."""
        ord_dvsn = "01" if price == 0 else "00"
        body = {
            "CANO": self._cfg.account_prefix,
            "ACNT_PRDT_CD": self._cfg.account_suffix,
            "PDNO": symbol,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price),
            "EXCG_ID_DVSN_CD": "KRX",
        }
        data = await self._c.post(_ORDER_PATH, tr_id=self._tr("buy"), body=body)
        order_no = data.get("output", {}).get("ODNO", "")
        logger.info("매수 주문 | {} {}주 @{} → 주문번호={}", symbol, qty, price or "시장가", order_no)
        return OrderResult(order_no=order_no, symbol=symbol, side="buy", qty=qty, price=price)

    async def sell(self, symbol: str, qty: int, price: int = 0) -> OrderResult:
        """시장가(price=0) 또는 지정가 매도."""
        ord_dvsn = "01" if price == 0 else "00"
        body = {
            "CANO": self._cfg.account_prefix,
            "ACNT_PRDT_CD": self._cfg.account_suffix,
            "PDNO": symbol,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price),
            "EXCG_ID_DVSN_CD": "KRX",
            "SLL_TYPE": "01",
        }
        data = await self._c.post(_ORDER_PATH, tr_id=self._tr("sell"), body=body)
        order_no = data.get("output", {}).get("ODNO", "")
        logger.info("매도 주문 | {} {}주 @{} → 주문번호={}", symbol, qty, price or "시장가", order_no)
        return OrderResult(order_no=order_no, symbol=symbol, side="sell", qty=qty, price=price)

    async def buy_overseas(self, symbol: str, excd: str, qty: int, price: float = 0.0) -> OrderResult:
        """해외 주식 매수. price=0 이면 시장가."""
        suffix = "mock" if self._cfg.kis_is_mock else "real"
        body = {
            "CANO": self._cfg.account_prefix,
            "ACNT_PRDT_CD": self._cfg.account_suffix,
            "OVRS_EXCG_CD": excd,
            "PDNO": symbol,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": f"{price:.2f}" if price else "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00",
        }
        data = await self._c.post(_OVRS_ORDER_PATH, tr_id=_TR[f"ovrs_buy_{suffix}"], body=body)
        order_no = data.get("output", {}).get("ODNO", "")
        logger.info("해외 매수 | {} {} {}주 @{} → {}", excd, symbol, qty, price or "시장가", order_no)
        return OrderResult(order_no=order_no, symbol=symbol, side="buy", qty=qty, price=int(price * 100))

    async def sell_overseas(self, symbol: str, excd: str, qty: int, price: float = 0.0) -> OrderResult:
        """해외 주식 매도. price=0 이면 시장가."""
        suffix = "mock" if self._cfg.kis_is_mock else "real"
        body = {
            "CANO": self._cfg.account_prefix,
            "ACNT_PRDT_CD": self._cfg.account_suffix,
            "OVRS_EXCG_CD": excd,
            "PDNO": symbol,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": f"{price:.2f}" if price else "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00",
        }
        data = await self._c.post(_OVRS_ORDER_PATH, tr_id=_TR[f"ovrs_sell_{suffix}"], body=body)
        order_no = data.get("output", {}).get("ODNO", "")
        logger.info("해외 매도 | {} {} {}주 @{} → {}", excd, symbol, qty, price or "시장가", order_no)
        return OrderResult(order_no=order_no, symbol=symbol, side="sell", qty=qty, price=int(price * 100))

    async def get_account(self) -> AccountSummary:
        """잔고 및 보유 종목 조회."""
        params = {
            "CANO": self._cfg.account_prefix,
            "ACNT_PRDT_CD": self._cfg.account_suffix,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        data = await self._c.get(_BALANCE_PATH, tr_id=self._tr("balance"), params=params)

        # 실서버: output1=보유종목, output2=계좌요약
        # 모의투자: output1=보유종목, output2=계좌요약 (동일 구조)
        summary_list = data.get("output2", [])
        summary = summary_list[0] if summary_list else {}
        net_asset     = int(float(summary.get("tot_evlu_amt", 0)))
        stocks_eval   = int(float(summary.get("scts_evlu_amt", 0)))
        total_purchase = int(float(summary.get("pchs_amt_smtl_amt", 0)))
        pnl_amount    = int(float(summary.get("evlu_pfls_smtl_amt", 0)))

        holdings = [
            HoldingItem(
                symbol=h.get("pdno", ""),
                name=h.get("prdt_name", ""),
                qty=int(h.get("hldg_qty", 0)),
                avg_price=float(h.get("pchs_avg_pric", 0)),
                current_price=int(h.get("prpr", 0)),
                pnl_amount=int(h.get("evlu_pfls_amt", 0)),
                pnl_rate=float(h.get("evlu_pfls_rt", 0)),
            )
            for h in data.get("output1", [])
            if int(h.get("hldg_qty", 0)) > 0
        ]

        return AccountSummary(
            net_asset=net_asset,
            stocks_eval=stocks_eval,
            total_purchase=total_purchase,
            pnl_amount=pnl_amount,
            holdings=holdings,
        )

    async def get_buyable_amount(self, symbol: str, price: int) -> int:
        """특정 종목을 해당 가격에 매수 가능한 금액 조회."""
        params = {
            "CANO": self._cfg.account_prefix,
            "ACNT_PRDT_CD": self._cfg.account_suffix,
            "PDNO": symbol,
            "ORD_UNPR": str(price),
            "ORD_DVSN": "00",
            "CMA_EVLU_AMT_ICLD_YN": "N",
            "OVRS_ICLD_YN": "N",
        }
        data = await self._c.get(_BUYABLE_PATH, tr_id=self._tr("buyable"), params=params)
        return int(data.get("output", {}).get("ord_psbl_cash", 0))

    async def get_filled_price(self, order_no: str) -> int:
        """시장가 주문의 실제 체결가 조회. 미체결 시 0 반환."""
        from datetime import date
        today = date.today().strftime("%Y%m%d")
        try:
            data = await self._c.get(
                _CCLD_PATH,
                tr_id=self._tr("ccld"),
                params={
                    "CANO": self._cfg.account_prefix,
                    "ACNT_PRDT_CD": self._cfg.account_suffix,
                    "INQR_STRT_DT": today,
                    "INQR_END_DT": today,
                    "SLL_BUY_DVSN_CD": "00",
                    "INQR_DVSN": "00",
                    "PDNO": "",
                    "CCLD_DVSN": "01",
                    "ORD_GNO_BRNO": "",
                    "ODNO": order_no,
                    "INQR_DVSN_3": "00",
                    "INQR_DVSN_1": "",
                    "CTX_AREA_FK100": "",
                    "CTX_AREA_NK100": "",
                },
            )
            rows = data.get("output1", [])
            for row in rows:
                if row.get("odno") == order_no:
                    return int(float(row.get("avg_prvs", 0)))
        except Exception as exc:
            logger.debug("체결가 조회 실패 | {}: {}", order_no, exc)
        return 0
