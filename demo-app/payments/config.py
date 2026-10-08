from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "payments"
    PORT: int = 8002
    HOST: str = "0.0.0.0"
    LOKI_URL: str = "http://loki:3100"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://jaeger:4318/v1/traces"

    # Operational configuration
    BASE_LATENCY_MS: float = 35.0
    FAILURE_RATE: float = 0.0

    # Fault injection state
    INJECTED_TIMEOUT_ACTIVE: bool = False
    INJECTED_TIMEOUT_DELAY_SEC: float = 8.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
