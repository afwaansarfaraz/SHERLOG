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

    # Database Configuration (PostgreSQL with SQLAlchemy)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sherlog"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis Streams & Queue Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_NAME: str = "sherlog:incidents:stream"
    REDIS_CONSUMER_GROUP: str = "sherlog:incident-workers"
    REDIS_DLQ_STREAM_NAME: str = "sherlog:incidents:dlq"
    WORKER_MAX_RETRIES: int = 3
    WORKER_CLAIM_TIMEOUT_MS: int = 30000
    WORKER_BLOCK_TIMEOUT_MS: int = 2000

    # Observability & Evidence Collection Tools Configuration
    PROMETHEUS_URL: str = "http://localhost:9090"
    LOKI_URL: str = "http://localhost:3100"
    JAEGER_URL: str = "http://localhost:16686"
    OBSERVABILITY_TIMEOUT_SECONDS: float = 5.0
    EVIDENCE_MAX_RESULTS: int = 100
    GIT_REPO_PATH: str = "."

    @property
    def sync_database_url(self) -> str:
        """Return SQLAlchemy-compatible URL, ensuring psycopg dialect if using postgresql."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
