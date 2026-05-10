"""KIS 주문 및 계좌 조회 API."""

from dataclasses import dataclass

from loguru import logger

from sagopalgo.api.rest import KisRestClient
from sagopalgo.config import get_settings

_ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"
_BALANCE_PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"
_BUYABLE_PATH = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"

_TR = {
    "buy_real": "TTTC0012U",
    "buy_mock": "VTTC0012U",
    "sell_real": "TTTC0011U",
    "sell_mock": "VTTC0011U",
    "balance_real": "TTTC8434R",
    "balance_mock": "VTTC8434R",
    "buyable_real": "TTTC8908R",
    "buyable_mock": "VTTC8908R",
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
    cash: int               # 예수금
    total_eval: int         # 총평가금액
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

    async def get_account(self) -> AccountSummary:
        """잔고 및 보유 종목 조회."""
        params = {
            "CANO": self._cfg.account_prefix,
            "ACNT_PRDT_CD": self._cfg.account_suffix,
            "AFHR_FLPR_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        data = await self._c.get(_BALANCE_PATH, tr_id=self._tr("balance"), params=params)

        output1 = data.get("output1", [{}])
        summary = output1[0] if output1 else {}
        cash = int(summary.get("dnca_tot_amt", 0))
        total_eval = int(summary.get("tot_evlu_amt", 0))

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
            for h in data.get("output2", [])
            if int(h.get("hldg_qty", 0)) > 0
        ]

        return AccountSummary(cash=cash, total_eval=total_eval, holdings=holdings)

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
