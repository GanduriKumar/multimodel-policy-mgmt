"""
Application configuration using pydantic-settings.

Loads settings from environment variables (and optional .env file) with sensible defaults.

Fields loaded (env var names in parentheses):
- app_env (APP_ENV)
- log_level (LOG_LEVEL)
- db_url (DB_URL or DATABASE_URL)
- api_key_header (API_KEY_HEADER)
- auth_hmac_secret (AUTH_HMAC_SECRET, API_KEY_SECRET, AUTH_SECRET, SECRET_KEY, APP_AUTH_SECRET)
- default_risk_threshold (DEFAULT_RISK_THRESHOLD)

Usage:
    from app.core.config import get_settings
    settings = get_settings()
    print(settings.db_url)
"""

from __future__ import annotations

import os
from functools import lru_cache


# Compatibility for Pydantic v2 (pydantic-settings) and v1 fallback
try:  # Pydantic v2 style
    from pydantic import Field, AliasChoices
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        # Environment / logging
        app_env: str = Field(default="development", alias="APP_ENV")
        log_level: str = Field(default="INFO", alias="LOG_LEVEL")

        # Database URL (accept DB_URL or DATABASE_URL)
        db_url: str = Field(
            default="sqlite:///./app.db",
            validation_alias=AliasChoices("DB_URL", "DATABASE_URL"),
        )

        # API key header name
        api_key_header: str = Field(default="x-api-key", alias="API_KEY_HEADER")

        # HMAC secret for API key hashing/verification - support multiple env names
        auth_hmac_secret: str = Field(
            default="dev-secret",
            validation_alias=AliasChoices(
                "AUTH_HMAC_SECRET", "API_KEY_SECRET", "AUTH_SECRET", "SECRET_KEY", "APP_AUTH_SECRET"
            ),
        )

        # Default risk threshold (0-100)
        default_risk_threshold: int = Field(
            default=80, alias="DEFAULT_RISK_THRESHOLD", ge=0, le=100
        )

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

except Exception:  # pragma: no cover - Pydantic v1 fallback
    from pydantic import BaseSettings, Field  # type: ignore

    class Settings(BaseSettings):  # type: ignore
        # Environment / logging
        app_env: str = Field(default="development")
        log_level: str = Field(default="INFO")

        # Database URL
        db_url: str = Field(default="sqlite:///./app.db")

        # API key header name
        api_key_header: str = Field(default="x-api-key")

        # HMAC secret
        auth_hmac_secret: str = Field(default="dev-secret")

        # Default risk threshold (0-100)
        default_risk_threshold: int = Field(default=80, ge=0, le=100)

        class Config:  # type: ignore
            env_file = ".env"
            env_file_encoding = "utf-8"
            # Map environment variables to fields (order matters)
            fields = {
                "db_url": {"env": ["DB_URL", "DATABASE_URL"]},
                "auth_hmac_secret": {
                    "env": [
                        "AUTH_HMAC_SECRET",
                        "API_KEY_SECRET",
                        "AUTH_SECRET",
                        "SECRET_KEY",
                        "APP_AUTH_SECRET",
                    ]
                },
                "app_env": {"env": ["APP_ENV"]},
                "log_level": {"env": ["LOG_LEVEL"]},
                "api_key_header": {"env": ["API_KEY_HEADER"]},
                "default_risk_threshold": {"env": ["DEFAULT_RISK_THRESHOLD"]},
            }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    """
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]
