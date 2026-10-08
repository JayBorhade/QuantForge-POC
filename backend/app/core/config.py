"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_LOCAL_ENVS = {"development", "local", "test"}
_DEFAULT_SECRET_PREFIXES = (
    "dev-secret-key-",
    "dev-jwt-secret-key-",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "QuantForge"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars!!",
        min_length=32,
    )
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://quantforge:quantforge_secret@localhost:5432/quantforge"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jwt_secret_key: str = Field(
        default="dev-jwt-secret-key-change-in-production-min-32!!",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cookie_secure: bool = False
    cookie_domain: str = "localhost"
    cookie_samesite: str = "lax"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@quantforge.io"

    rate_limit_per_minute: int = 60
    cors_origins: List[str] = ["http://localhost:3000"]

    # Encryption (required outside local/test environments)
    encryption_key: str = ""

    # CSRF
    csrf_enabled: bool = True

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""

    @model_validator(mode="after")
    def validate_environment_security(self):
        environment = self.app_env.strip().lower()
        if environment in _LOCAL_ENVS:
            return self

        if self.debug:
            raise ValueError("DEBUG must be false outside local/test environments")
        if any(self.secret_key.startswith(prefix) for prefix in _DEFAULT_SECRET_PREFIXES):
            raise ValueError("SECRET_KEY must be explicitly configured outside local/test environments")
        if self.jwt_secret_key.startswith("dev-jwt-secret-key-"):
            raise ValueError("JWT_SECRET_KEY must be explicitly configured outside local/test environments")
        if self.database_url == "postgresql+asyncpg://quantforge:quantforge_secret@localhost:5432/quantforge":
            raise ValueError("DATABASE_URL must be explicitly configured outside local/test environments")
        if not self.encryption_key:
            raise ValueError("ENCRYPTION_KEY must be explicitly configured outside local/test environments")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true outside local/test environments")
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        if not self.cors_origins:
            raise ValueError("CORS_ORIGINS must contain at least one trusted origin")
        if self.csrf_enabled is not True:
            raise ValueError("CSRF_ENABLED must remain true outside local/test environments")
        return self

    @property
    def effective_encryption_key(self) -> str:
        return self.encryption_key or self.secret_key

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
