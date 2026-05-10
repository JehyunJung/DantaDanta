"""KIS REST API 기반 클라이언트."""

from typing import Any

import httpx
from loguru import logger

from dantadanta.api.auth import TokenManager, get_token_manager
from dantadanta.config import Settings, get_settings


class KisRestClient:
    """KIS REST API 클라이언트.

    토큰 자동 주입, 401 시 1회 재시도, 공통 헤더 처리.
    auth를 명시하지 않으면 프로세스 싱글턴 TokenManager를 사용.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        auth: TokenManager | None = None,
    ) -> None:
        self._cfg = settings or get_settings()
        self._auth = auth or get_token_manager()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "KisRestClient":
        self._client = httpx.AsyncClient(base_url=self._cfg.kis_base_url, timeout=10)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, path: str, *, tr_id: str, params: dict | None = None) -> dict:
        return await self._request("GET", path, tr_id=tr_id, params=params)

    async def post(self, path: str, *, tr_id: str, body: dict | None = None) -> dict:
        return await self._request("POST", path, tr_id=tr_id, json=body)

    async def _request(self, method: str, path: str, *, tr_id: str, **kwargs: Any) -> dict:
        assert self._client, "async with 블록 안에서 사용하세요"

        for attempt in range(2):
            headers = await self._build_headers(tr_id)
            resp = await self._client.request(method, path, headers=headers, **kwargs)

            if resp.status_code == 401 and attempt == 0:
                logger.warning("401 수신 — 토큰 재발급 후 재시도")
                self._auth.invalidate()
                continue

            if not resp.is_success:
                logger.error("HTTP 오류 | status={} body={}", resp.status_code, resp.text)
            resp.raise_for_status()
            data = resp.json()

            if data.get("rt_cd") != "0":
                logger.error(
                    "KIS API 오류 | tr_id={} code={} msg={}",
                    tr_id,
                    data.get("msg_cd"),
                    data.get("msg1"),
                )
                raise KisApiError(tr_id, data.get("msg_cd", ""), data.get("msg1", ""))

            return data

        raise RuntimeError("재시도 후에도 요청 실패")

    async def _build_headers(self, tr_id: str) -> dict:
        token = await self._auth.get_access_token()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self._cfg.kis_app_key,
            "appsecret": self._cfg.kis_app_secret,
            "tr_id": tr_id,
            "custtype": "P",  # 개인
        }


class KisApiError(Exception):
    def __init__(self, tr_id: str, code: str, message: str) -> None:
        super().__init__(f"[{tr_id}] {code}: {message}")
        self.tr_id = tr_id
        self.code = code
        self.message = message
