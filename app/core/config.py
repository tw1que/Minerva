from __future__ import annotations

import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Minerva"
    app_env: str = Field(default="dev", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    api_prefix: str = "/api"

    database_url: str = Field(
        default="postgresql+psycopg://minerva:minerva@db:5432/minerva",
        alias="DATABASE_URL",
    )

    auto_create_db: bool = Field(default=True, alias="AUTO_CREATE_DB")
    db_connect_retries: int = Field(default=30, alias="DB_CONNECT_RETRIES")
    db_connect_delay: float = Field(default=1.0, alias="DB_CONNECT_DELAY")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=720, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    initial_admin_username: str = Field(default="admin", alias="INITIAL_ADMIN_USERNAME")
    initial_admin_password: str = Field(default="admin123", alias="INITIAL_ADMIN_PASSWORD")

    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")
    medical_traceability: bool = Field(default=False, alias="MEDICAL_TRACEABILITY")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return []
            if cleaned.startswith("["):
                return json.loads(cleaned)
            return [item.strip() for item in cleaned.split(",") if item.strip()]
        return []

    @field_validator("debug", mode="before")
    @classmethod
    def _parse_debug(cls, value: object) -> bool:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if cleaned in {"1", "true", "yes", "on", "debug"}:
                return True
            if cleaned in {"release", "prod", "production"}:
                return False
            if cleaned in {"0", "false", "no", "off", ""}:
                return False
        return bool(value)


settings = Settings()
