"""KIS 주문 및 계좌 조회 API."""

from dataclasses import dataclass

from loguru import logger

from dantadanta.api.rest import KisRestClient
from dantadanta.config import get_settings

_ORDER_PATH       = "/uapi/domestic-stock/v1/trading/order-cash"
_BALANCE_PATH     = "/uapi/domestic-stock/v1/trading/inquire-balance"
_OVRS_BALANCE_PATH = "/uapi/overseas-stock/v1/trading/inquire-balance"
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
    "ovrs_balance_real": "TTTS3012R",
    "ovrs_balance_mock": "VTTS3012R",
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
    overseas_cash: int = 0  # 해외 예수금 (원화 환산)


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

        # 해외 잔고 합산
        overseas_cash = 0
        try:
            ovrs_holdings, ovrs_stocks_eval, ovrs_purchase, ovrs_pnl, overseas_cash = await self._get_overseas_balance()
            holdings       += ovrs_holdings
            stocks_eval    += ovrs_stocks_eval
            total_purchase += ovrs_purchase
            pnl_amount     += ovrs_pnl
            net_asset      += ovrs_stocks_eval + overseas_cash
        except Exception as exc:
            import traceback
            logger.warning("해외 잔고 조회 실패: {} | {}", exc, traceback.format_exc())

        return AccountSummary(
            net_asset=net_asset,
            stocks_eval=stocks_eval,
            total_purchase=total_purchase,
            pnl_amount=pnl_amount,
            holdings=holdings,
            overseas_cash=overseas_cash,
        )

    async def _get_overseas_balance(self) -> tuple[list[HoldingItem], int, int, int, int]:
        """해외 주식 잔고 조회. (holdings, stocks_eval_krw, total_purchase_krw, pnl_krw, cash_krw)"""
        suffix = "real" if not self._cfg.kis_is_mock else "mock"
        tr_id = _TR[f"ovrs_balance_{suffix}"]
        all_holdings: list[HoldingItem] = []
        total_eval = total_purchase = total_pnl = overseas_cash = 0

        for crcy in ("USD", "HKD", "JPY", "CNY", "EUR"):
            params = {
                "CANO": self._cfg.account_prefix,
                "ACNT_PRDT_CD": self._cfg.account_suffix,
                "OVRS_EXCG_CD": "NASD",
                "TR_CRCY_CD": crcy,
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": "",
            }
            try:
                data = await self._c.get(_OVRS_BALANCE_PATH, tr_id=tr_id, params=params)
            except Exception:
                continue

            output2 = data.get("output2", {})
            summary = (output2[0] if output2 else {}) if isinstance(output2, list) else output2

            # output2는 KRW 기준 — 매수금액 + 손익으로 평가금액 계산
            pchs_krw = int(float(summary.get("frcr_pchs_amt1", 0)))          # KRW 매수금액
            pnl_krw  = int(float(summary.get("tot_evlu_pfls_amt", 0)))        # KRW 평가손익
            eval_total_krw = pchs_krw + pnl_krw                               # KRW 평가금액

            for h in data.get("output1", []):
                qty = int(h.get("ovrs_cblc_qty", 0))
                if qty <= 0:
                    continue

                # output1은 USD 기준 — output2 비율로 KRW 환산
                usd_eval  = float(h.get("ovrs_stck_evlu_amt", 0))             # USD 평가금액
                usd_total = float(summary.get("frcr_buy_amt_smtl1", 0)) or float(summary.get("frcr_pchs_amt1", 0)) or 1
                # KRW 환산: 종목 USD 비중 × 전체 KRW
                eval_krw  = int(usd_eval / usd_total * eval_total_krw) if usd_total else 0

                avg_price_usd = float(h.get("pchs_avg_pric", 0))
                pnl_rate      = float(h.get("evlu_pfls_rt", 0))
                pfls_usd      = float(h.get("frcr_evlu_pfls_amt", 0))
                pchs_usd      = float(h.get("frcr_pchs_amt1", 0))
                pnl_amt_krw   = int(pfls_usd / usd_total * pnl_krw) if usd_total else 0

                all_holdings.append(HoldingItem(
                    symbol=h.get("ovrs_pdno", ""),
                    name=h.get("ovrs_item_name", ""),
                    qty=qty,
                    avg_price=avg_price_usd,
                    current_price=eval_krw // qty if qty else 0,
                    pnl_amount=pnl_amt_krw,
                    pnl_rate=pnl_rate,
                ))
                total_eval     += eval_krw
                total_purchase += int(pchs_usd / usd_total * pchs_krw) if usd_total else 0
                total_pnl      += pnl_amt_krw

            if all_holdings:
                break

        return all_holdings, total_eval, total_purchase, total_pnl, overseas_cash

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
