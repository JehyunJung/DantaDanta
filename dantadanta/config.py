from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # KIS API
    kis_app_key: str
    kis_app_secret: str
    kis_account_no: str
    kis_is_mock: bool = True

    # OpenAI
    openai_api_key: str = ""

    # 매매 설정
    budget_limit: int = 1_000_000
    max_position_ratio: float = 0.2

    # 알림
    telegram_token: str = ""
    telegram_chat_id: str = ""

    @field_validator("max_position_ratio")
    @classmethod
    def validate_ratio(cls, v: float) -> float:
        if not 0 < v <= 1:
            raise ValueError("max_position_ratio는 0 초과 1 이하여야 합니다")
        return v

    @property
    def kis_base_url(self) -> str:
        if self.kis_is_mock:
            return "https://openapivts.koreainvestment.com:29443"
        return "https://openapi.koreainvestment.com:9443"

    @property
    def kis_ws_url(self) -> str:
        if self.kis_is_mock:
            return "ws://ops.koreainvestment.com:31000"
        return "ws://ops.koreainvestment.com:21000"

    @property
    def account_prefix(self) -> str:
        """계좌번호에서 앞 8자리 반환 (예: 12345678-01 → 12345678)"""
        return self.kis_account_no.split("-")[0]

    @property
    def account_suffix(self) -> str:
        """계좌번호에서 뒤 2자리 반환 (예: 12345678-01 → 01)"""
        parts = self.kis_account_no.split("-")
        return parts[1] if len(parts) > 1 else "01"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
