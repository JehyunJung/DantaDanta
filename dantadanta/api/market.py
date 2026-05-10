"""KIS 시세/차트 데이터 조회."""

from datetime import date

import pandas as pd

from dantadanta.api.rest import KisRestClient

_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
_DAILY_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
_MINUTE_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"


class MarketApi:
    def __init__(self, client: KisRestClient) -> None:
        self._c = client

    async def get_price(self, symbol: str) -> dict:
        """현재가 단건 조회."""
        data = await self._c.get(
            _PRICE_PATH,
            tr_id="FHKST01010100",
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
        )
        return data["output"]

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
