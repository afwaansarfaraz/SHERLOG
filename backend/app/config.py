"""Sherlog Backend - Configuration Module.

Loads configuration from environment variables with strong typing using Pydantic Settings.
Never hardcodes secrets.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine project repository root (three levels up from backend/app/config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ROOT_ENV_FILE = PROJECT_ROOT / ".env"

# Preload project-root .env into os.environ if present, without overriding shell variables
if ROOT_ENV_FILE.exists():
    load_dotenv(ROOT_ENV_FILE, override=False)


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

    # LLM & AI Investigation Provider Configuration
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = None
    LLM_API_KEY: Optional[str] = None  # Backward-compatible fallback for generic configurations
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_RETRIES: int = 2

    # RAG & Knowledge Retrieval Configuration
    RAG_ENABLED: bool = True
    EMBEDDING_PROVIDER: str = "fastembed"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: Optional[str] = None
    RAG_TOP_K: int = 3
    RAG_SIMILARITY_THRESHOLD: float = 0.35

    @property
    def effective_groq_api_key(self) -> Optional[str]:
        """Return the active Groq API key with proper precedence:
        1. os.environ['GROQ_API_KEY']
        2. self.GROQ_API_KEY (from .env or config)
        3. os.environ['LLM_API_KEY']
        4. self.LLM_API_KEY (from .env or config)
        """
        for candidate in (
            os.environ.get("GROQ_API_KEY"),
            self.GROQ_API_KEY,
            os.environ.get("LLM_API_KEY"),
            self.LLM_API_KEY,
        ):
            if candidate and candidate.strip():
                return candidate.strip()
        return None

    @property
    def is_llm_configured(self) -> bool:
        """Check if an API key is present without exposing its value."""
        return bool(self.effective_groq_api_key)

    def safe_dict(self) -> dict:
        """Export settings dictionary with all sensitive credentials redacted."""
        data = self.model_dump()
        for secret_key in ("WEBHOOK_SECRET", "API_KEY", "GROQ_API_KEY", "LLM_API_KEY", "EMBEDDING_API_KEY"):
            if data.get(secret_key):
                data[secret_key] = "[REDACTED]"
        return data

    @property
    def sync_database_url(self) -> str:
        """Return SQLAlchemy-compatible URL, ensuring psycopg dialect if using postgresql."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    """Return Settings instance, picking up any runtime environment updates."""
    return Settings()


settings = get_settings()
