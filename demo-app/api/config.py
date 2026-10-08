from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "api"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOKI_URL: str = "http://loki:3100"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://jaeger:4318/v1/traces"

    # Upstream service dependencies
    ORDERS_SERVICE_URL: str = "http://orders:8001"
    ORDERS_TIMEOUT_SEC: float = 5.0

    # Webhook security
    WEBHOOK_SECRET: str = "sherlog-webhook-secret-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
