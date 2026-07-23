from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_secret_key: SecretStr
    lms_key_pepper: SecretStr
    database_url: str
    telegram_bot_token: SecretStr | None = None
    telegram_support_chat_id: int | None = None
    media_root: Path = Path("/data/media")
    log_dir: Path = Path("/data/logs")
    admin_host: str = "0.0.0.0"
    admin_port: int = 8000
    public_base_url: str = "http://localhost:8000"
    timezone: str = "Europe/Moscow"
    bot_polling: bool = True

    @field_validator("telegram_bot_token", "telegram_support_chat_id", mode="before")
    @classmethod
    def empty_optional_value_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if len(self.app_secret_key.get_secret_value()) < 32:
            raise ValueError("APP_SECRET_KEY должен содержать не меньше 32 символов")
        if len(self.lms_key_pepper.get_secret_value()) < 32:
            raise ValueError("LMS_KEY_PEPPER должен содержать не меньше 32 символов")
        if self.app_env == "production":
            if not self.public_base_url.startswith("https://"):
                raise ValueError("В production PUBLIC_BASE_URL должен начинаться с https://")
            if "zero_semester:zero_semester@" in self.database_url:
                raise ValueError("В production нельзя использовать стандартный пароль PostgreSQL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
