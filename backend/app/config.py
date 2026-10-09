"""Sherlog Backend - Configuration Module.

Loads configuration from environment variables with strong typing using Pydantic Settings.
Never hardcodes secrets.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Sherlog Incident Backend"
    APP_ENV: str = "development"
    DEBUG: bool = False
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api"

    # Security & Authentication (never hardcoded, set via environment)
    WEBHOOK_SECRET: Optional[str] = None
    API_KEY: Optional[str] = None

    # Infrastructure placeholders (used in subsequent phases)
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
