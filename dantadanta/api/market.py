"""KIS 시세/차트 데이터 조회."""

from datetime import date

import httpx
import pandas as pd

from dantadanta.api.auth import TokenManager
from dantadanta.api.rest import KisRestClient
from dantadanta.config import get_settings

_PRICE_PATH        = "/uapi/domestic-stock/v1/quotations/inquire-price"
_DAILY_CHART_PATH  = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
_MINUTE_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
_OVRS_PRICE_PATH   = "/uapi/overseas-price/v1/quotations/price"
_OVRS_CHART_PATH   = "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice"

# 해외 시세 전용 실서버 URL (모의투자 서버에는 해외 시세 API 없음)
_REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"

# 해외 봉 종류: 0=일, 1=주, 2=월
_OVRS_GUBN = {"D": "0", "W": "1", "M": "2", "Y": "2"}


class MarketApi:
    def __init__(self, client: KisRestClient) -> None:
        self._c = client
        self._cfg = get_settings()
        # 해외 API는 실거래 앱키 필요 (모의 앱키로 실서버 호출 불가)
        if self._cfg.kis_is_mock and self._cfg.kis_real_app_key:
            from dantadanta.config import Settings
            real_cfg = Settings(
                kis_app_key=self._cfg.kis_real_app_key,
                kis_app_secret=self._cfg.kis_real_app_secret,
                kis_account_no=self._cfg.kis_account_no,
                kis_is_mock=False,
            )
            self._real_auth = TokenManager(real_cfg)
        else:
            self._real_auth = self._c._auth

    async def _ovrs_get(self, path: str, tr_id: str, params: dict) -> dict:
        """해외 시세 조회 — 항상 실서버로 직접 호출 (실서버 토큰 사용)."""
        token = await self._real_auth.get_access_token()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self._cfg.kis_app_key,
            "appsecret": self._cfg.kis_app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        async with httpx.AsyncClient(base_url=_REAL_BASE_URL, timeout=10) as client:
            resp = await client.get(path, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_price(self, symbol: str) -> dict:
        """현재가 단건 조회."""
        data = await self._c.get(
            _PRICE_PATH,
            tr_id="FHKST01010100",
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
        )
        return data["output"]

    async def get_name(self, symbol: str) -> str:
        """종목명 조회 (일봉 output1 활용)."""
        from datetime import date, timedelta
        end = date.today()
        start = end - timedelta(days=7)
        data = await self._c.get(
            _DAILY_CHART_PATH,
            tr_id="FHKST03010100",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "1",
            },
        )
        return data.get("output1", {}).get("hts_kor_isnm", symbol)

    async def get_daily_chart(
        self,
        symbol: str,
        start: date,
        end: date,
        period: str = "D",
    ) -> pd.DataFrame:
        """일봉/주봉/월봉 차트 조회.

        period: D=일, W=주, M=월, Y=년
        """
        data = await self._c.get(
            _DAILY_CHART_PATH,
            tr_id="FHKST03010100",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": period,
                "FID_ORG_ADJ_PRC": "1",
            },
        )
        rows = data.get("output2", [])
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = df.rename(columns={
            "stck_bsop_date": "date",
            "stck_clpr": "close",
            "stck_oprc": "open",
            "stck_hgpr": "high",
            "stck_lwpr": "low",
            "acml_vol": "volume",
        })
        numeric_cols = ["close", "open", "high", "low", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        return df.sort_values("date").reset_index(drop=True)

    async def get_overseas_price(self, symbol: str, excd: str) -> dict:
        """해외 주식 현재가 조회."""
        data = await self._ovrs_get(
            _OVRS_PRICE_PATH,
            tr_id="HHDFS00000300",
            params={"AUTH": "", "EXCD": excd, "SYMB": symbol},
        )
        return data.get("output", {})

    async def get_overseas_chart(
        self,
        symbol: str,
        excd: str,
        end: date,
        period: str = "D",
    ) -> pd.DataFrame:
        """해외 주식 일/주/월봉 차트 조회."""
        gubn = _OVRS_GUBN.get(period, "0")
        data = await self._ovrs_get(
            _OVRS_CHART_PATH,
            tr_id="HHDFS76240000",
            params={
                "AUTH": "",
                "EXCD": excd,
                "SYMB": symbol,
                "GUBN": gubn,
                "BYMD": end.strftime("%Y%m%d"),
                "MODP": "1",
            },
        )
        rows = data.get("output2", [])
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = df.rename(columns={
            "stck_bsop_date": "date",
            "ovrs_nmix_prpr": "close",
            "ovrs_nmix_oprc": "open",
            "ovrs_nmix_hgpr": "high",
            "ovrs_nmix_lwpr": "low",
            "acml_vol": "volume",
        })
        numeric_cols = ["close", "open", "high", "low", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        return df.sort_values("date").reset_index(drop=True)

    async def get_minute_chart(self, symbol: str, hour: str = "090000") -> pd.DataFrame:
        """분봉 차트 조회. hour: HHMMSS 형식."""
        data = await self._c.get(
            _MINUTE_CHART_PATH,
            tr_id="FHKST03010200",
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": hour,
                "FID_PW_DATA_INCU_YN": "Y",
                "FID_ETC_CLS_CODE": "",
            },
        )
        rows = data.get("output2", [])
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = df.rename(columns={
            "stck_cntg_hour": "time",
            "stck_prpr": "close",
            "stck_oprc": "open",
            "stck_hgpr": "high",
            "stck_lwpr": "low",
            "cntg_vol": "volume",
        })
        numeric_cols = ["close", "open", "high", "low", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.reset_index(drop=True)
