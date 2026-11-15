"""Application settings, read from the environment (or a local .env file).

Every value has a development default so the service and the test suite
run with zero configuration. Real deployments override the secret values
through the environment; the deployment .env file is never committed.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "fde-backend-service"
    environment: str = "development"

    # PostgreSQL in Docker Compose and CI. The test suite may point this
    # at a SQLite file instead; the models use portable column types.
    database_url: str = "postgresql+asyncpg://fde:fde_password@localhost:5432/fde"

    # JWT. jwt_secret must be overridden outside local development.
    jwt_secret: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Optional seed admin, created at startup when both values are set
    # and no user with that email exists yet.
    admin_email: str | None = None
    admin_password: str | None = None

    # Webhook delivery behaviour.
    webhook_max_attempts: int = 3
    webhook_backoff_base_seconds: float = 1.0
    webhook_timeout_seconds: float = 5.0

    # Open-Meteo integration cache lifetime.
    weather_cache_ttl_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
