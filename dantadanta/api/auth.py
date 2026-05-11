"""KIS OAuth 액세스 토큰 및 WebSocket 접속키 관리."""

import asyncio
import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import httpx
from loguru import logger

from dantadanta.config import Settings, get_settings

_TOKEN_ENDPOINT = "/oauth2/tokenP"
_WS_KEY_ENDPOINT = "/oauth2/Approval"
_REFRESH_BEFORE_SECONDS = 300  # 만료 5분 전에 갱신
_TOKEN_CACHE_FILE = Path(".token_cache.json")


class TokenManager:
    """액세스 토큰 발급 및 자동 갱신.

    - 메모리 캐시: 같은 프로세스 내 중복 발급 방지
    - 파일 캐시: 프로세스 재시작 후에도 유효한 토큰 재사용 (KIS는 24시간 유효)
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._cfg = settings or get_settings()
        self._access_token: str = ""
        self._expires_at: datetime = datetime.min
        self._ws_approval_key: str = ""
        self._lock = asyncio.Lock()
        self._load_cache()

    @property
    def base_url(self) -> str:
        return self._cfg.kis_base_url

    async def get_access_token(self) -> str:
        """유효한 액세스 토큰 반환. 만료 임박 시 자동 갱신."""
        async with self._lock:
            if self._is_token_valid():
                return self._access_token
            await self._issue_token()
            return self._access_token

    async def get_ws_approval_key(self) -> str:
        """WebSocket 접속키 반환. 없으면 발급."""
        async with self._lock:
            if not self._ws_approval_key:
                await self._issue_ws_approval_key()
            return self._ws_approval_key

    def invalidate(self) -> None:
        """토큰 강제 무효화 (401 응답 수신 시 사용). 이미 무효화됐으면 스킵."""
        if not self._access_token:
            return
        self._access_token = ""
        self._expires_at = datetime.min
        self._ws_approval_key = ""
        _TOKEN_CACHE_FILE.unlink(missing_ok=True)

    def _is_token_valid(self) -> bool:
        if not self._access_token:
            return False
        return datetime.now() < self._expires_at - timedelta(seconds=_REFRESH_BEFORE_SECONDS)

    def _load_cache(self) -> None:
        """파일에서 캐시된 토큰 로드. 앱키가 다르거나 만료됐으면 무시."""
        if not _TOKEN_CACHE_FILE.exists():
            return
        try:
            data = json.loads(_TOKEN_CACHE_FILE.read_text())
            if data.get("app_key") != self._cfg.kis_app_key:
                return  # 다른 앱키의 토큰
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.now() >= expires_at - timedelta(seconds=_REFRESH_BEFORE_SECONDS):
                return  # 이미 만료 임박
            self._access_token = data["access_token"]
            self._expires_at = expires_at
            logger.info(
                "캐시된 토큰 재사용 | 만료: {}",
                self._expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as exc:
            logger.debug("토큰 캐시 로드 실패 (무시): {}", exc)

    def _save_cache(self) -> None:
        try:
            _TOKEN_CACHE_FILE.write_text(json.dumps({
                "app_key": self._cfg.kis_app_key,
                "access_token": self._access_token,
                "expires_at": self._expires_at.isoformat(),
            }))
        except Exception as exc:
            logger.debug("토큰 캐시 저장 실패 (무시): {}", exc)

    async def _issue_token(self) -> None:
        payload = {
            "grant_type": "client_credentials",
            "appkey": self._cfg.kis_app_key,
            "appsecret": self._cfg.kis_app_secret,
        }
        for attempt in range(3):
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}{_TOKEN_ENDPOINT}",
                    json=payload,
                    timeout=10,
                )
            if resp.is_success:
                break
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if resp.status_code == 403 and body.get("error_code") == "EGW00133":
                wait = 62
                logger.warning("토큰 발급 1분 제한 — {}초 후 재시도 ({}/3)", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            logger.error("토큰 발급 실패 | status={} body={}", resp.status_code, resp.text)
            resp.raise_for_status()
        else:
            resp.raise_for_status()
        data = resp.json()

        self._access_token = data["access_token"]
        if "expires_in" in data:
            self._expires_at = datetime.now() + timedelta(seconds=int(data["expires_in"]))
        elif "access_token_token_expired" in data:
            self._expires_at = datetime.strptime(
                data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S"
            )
        else:
            self._expires_at = datetime.now() + timedelta(hours=24)

        self._save_cache()
        logger.info("액세스 토큰 발급 완료 | 만료: {}", self._expires_at.strftime("%Y-%m-%d %H:%M:%S"))

    async def _issue_ws_approval_key(self) -> None:
        payload = {
            "grant_type": "client_credentials",
            "appkey": self._cfg.kis_app_key,
            "secretkey": self._cfg.kis_app_secret,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}{_WS_KEY_ENDPOINT}",
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

        self._ws_approval_key = data["approval_key"]
        logger.info("WebSocket 접속키 발급 완료")


@lru_cache(maxsize=1)
def get_token_manager() -> TokenManager:
    """프로세스 내 싱글턴 TokenManager."""
    return TokenManager()
