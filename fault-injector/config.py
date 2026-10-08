from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "fault-injector"
    PORT: int = 8003
    HOST: str = "0.0.0.0"
    LOKI_URL: str = "http://loki:3100"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://jaeger:4318/v1/traces"

    API_SERVICE_URL: str = "http://api:8000"
    ORDERS_SERVICE_URL: str = "http://orders:8001"
    PAYMENTS_SERVICE_URL: str = "http://payments:8002"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
