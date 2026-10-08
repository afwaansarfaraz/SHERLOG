from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "orders"
    PORT: int = 8001
    HOST: str = "0.0.0.0"
    LOKI_URL: str = "http://loki:3100"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://jaeger:4318/v1/traces"

    # Database connection parameters
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@postgres:5432/sherlog"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_TIMEOUT: float = 2.0

    # Downstream payments service
    PAYMENTS_SERVICE_URL: str = "http://payments:8002"
    PAYMENTS_TIMEOUT_SEC: float = 2.5

    # Injected fault controls
    INJECTED_SLOW_QUERY_ACTIVE: bool = False
    INJECTED_SLOW_QUERY_DELAY_SEC: float = 1.8
    INJECTED_POOL_EXHAUSTION_ACTIVE: bool = False
    INJECTED_CONFIG_ERROR_ACTIVE: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
