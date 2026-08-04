from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values are injected by docker-compose (see docker-compose.yml) but a
    local .env file is also supported for running outside of Docker.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = "Ren Event Ticketing System"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/ren"

    # Security / JWT
    SECRET_KEY: str = "supersecretkeychangethisinproduction2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS — comma-separated list of allowed origins
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Frontend base URL — used to build Stripe success/cancel redirect URLs.
    FRONTEND_URL: str = "http://localhost:3000"

    # Public base URL of THIS backend — used to build absolute URLs for
    # uploaded files (avatars) that the frontend/browser loads directly.
    BACKEND_URL: str = "http://localhost:8000"

    # Local uploads (served statically at /uploads). Fine for dev; swap for
    # object storage (S3/GCS) in production.
    UPLOAD_DIR: str = "uploads"
    MAX_AVATAR_BYTES: int = 5 * 1024 * 1024  # 5 MB
    MAX_EVENT_IMAGE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Stripe (test-mode keys for now). Loaded from the environment; never
    # commit real keys. STRIPE_WEBHOOK_SECRET is the signing secret shown when
    # you register the webhook endpoint (or run `stripe listen` locally).
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    # ISO 4217 currency for Checkout line items (lowercase, e.g. "usd", "gbp").
    STRIPE_CURRENCY: str = "usd"

    # Email / SMTP. When EMAIL_ENABLED is false (or SMTP_HOST is blank) emails
    # are written to the log instead of sent — a "console backend" for local
    # dev. Point these at a real SMTP relay (Mailgun/Resend SMTP, etc.) in prod.
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    EMAILS_FROM_EMAIL: str = "no-reply@ren.local"
    EMAILS_FROM_NAME: str = "Ren"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env once per process)."""
    return Settings()


settings = get_settings()
