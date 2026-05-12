"""KIS 시세/차트 데이터 조회."""

import logging
from datetime import date

import httpx
import pandas as pd

from dantadanta.api.auth import TokenManager
from dantadanta.api.rest import KisRestClient
from dantadanta.config import get_settings

logger = logging.getLogger(__name__)

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
        # 실거래 모드에서만 실서버 직접 호출용 인증 설정 (해외 KIS API)
        if not self._cfg.kis_is_mock:
            if self._cfg.kis_real_app_key:
                from dantadanta.config import Settings
                real_cfg = Settings(
                    kis_app_key=self._cfg.kis_real_app_key,
                    kis_app_secret=self._cfg.kis_real_app_secret,
                    kis_account_no=self._cfg.kis_account_no,
                    kis_is_mock=False,
                )
                self._real_auth = TokenManager(real_cfg)
                self._real_app_key = self._cfg.kis_real_app_key
                self._real_app_secret = self._cfg.kis_real_app_secret
            else:
                self._real_auth = self._c._auth
                self._real_app_key = self._cfg.kis_app_key
                self._real_app_secret = self._cfg.kis_app_secret

    async def _ovrs_get(self, path: str, tr_id: str, params: dict) -> dict:
        """해외 시세 조회 — 항상 실서버로 직접 호출 (실서버 토큰 사용)."""
        token = await self._real_auth.get_access_token()
        app_key = self._real_app_key
        app_secret = self._real_app_secret
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        async with httpx.AsyncClient(base_url=_REAL_BASE_URL, timeout=10) as client:
            resp = await client.get(path, headers=headers, params=params)
        if not resp.is_success:
            logger.warning("해외 API 오류 | %s %s | body=%s", tr_id, params.get("SYMB", ""), resp.text[:300])
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
        """해외 주식 현재가 조회 — yfinance 사용. last(USD) + last_krw(원화 환산) 반환."""
        import asyncio
        import yfinance as yf

        def _fetch() -> dict:
            # 환율 조회 (USDKRW=X)
            try:
                fx = yf.Ticker("USDKRW=X").fast_info
                rate = getattr(fx, "last_price", None) or getattr(fx, "regularMarketPrice", None) or 1400.0
            except Exception:
                rate = 1400.0

            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            last = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None) or 0.0
            return {"last": str(last), "last_krw": str(int(last * rate)), "usdkrw": str(rate)}

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_overseas_chart(
        self,
        symbol: str,
        excd: str,
        end: date,
        period: str = "D",
    ) -> pd.DataFrame:
        """해외 주식 일봉 차트 조회 — yfinance 사용 (KIS 해외 시세 API 대체)."""
        import asyncio
        import yfinance as yf

        start = end - __import__("datetime").timedelta(days=200)

        def _fetch() -> pd.DataFrame:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start.strftime("%Y-%m-%d"),
                                end=(end + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d"),
                                interval="1d", auto_adjust=True)
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df = df.rename(columns={
                "Date": "date", "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume",
            })
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            return df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

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

    async def collect_hourly_bars(self, symbol: str) -> int:
        """분봉을 수집해 완료된 시간봉을 bar_store에 적재. 추가된 봉 수 반환."""
        from datetime import datetime
        from dantadanta.engine.bar_store import save_bars

        now = datetime.now()
        df = await self.get_minute_chart(symbol, hour=now.strftime("%H%M%S"))
        if df.empty or "time" not in df.columns:
            return 0

        today = now.strftime("%Y%m%d")
        df["dt"] = pd.to_datetime(
            today + df["time"].astype(str).str.zfill(6), format="%Y%m%d%H%M%S"
        )
        df = df.set_index("dt").sort_index()

        hourly = df.resample("1h").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        ).dropna(subset=["close"])

        # 현재 진행 중인 봉은 제외 (완료된 봉만)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        hourly = hourly[hourly.index < current_hour]
        if hourly.empty:
            return 0

        hourly = hourly.reset_index().rename(columns={"dt": "dt"})
        return save_bars(symbol, hourly)
