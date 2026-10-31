"""
Central application settings.

Every environment variable the backend reads is declared here, so there is one
place to look when configuring a deployment. Values come from the process
environment or a `.env` file (see `.env.example` at the repo root).
"""

from __future__ import annotations

import logging
import secrets
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # "development" or "production". Production refuses to start with insecure defaults.
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ---- Database ----
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/stockpilot"
    # Connection used for LISTEN/NOTIFY. Pooled connections (e.g. Neon's pooler)
    # do not support LISTEN, so hosted setups point this at the direct endpoint.
    # Falls back to DATABASE_URL when empty.
    DIRECT_DATABASE_URL: str = ""
    DB_ECHO: bool = False

    # ---- Auth ----
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOW_REGISTRATION: bool = True

    # Optional admin bootstrap: when all three are set, the user is created on
    # startup (if missing) and given the admin role.
    ADMIN_USERNAME: str = ""
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    SEED_RBAC: bool = True

    # ---- Password reset ----
    # Public URL of the web app; reset links point here.
    APP_BASE_URL: str = "http://localhost:8080"
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # Optional SMTP for "forgot password" emails. Without it, admins hand out
    # reset links from the Users & Roles page instead.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True

    # Comma separated list of allowed browser origins.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- Realtime / outbox ----
    REALTIME_LISTEN_CHANNEL: str = "realtime_events"
    OUTBOX_LISTEN_CHANNEL: str = "analytics_outbox"
    OUTBOX_BATCH_SIZE: int = 50
    OUTBOX_POLL_TIMEOUT: int = 10
    OUTBOX_MAX_ATTEMPTS: int = 8
    OUTBOX_MAX_BACKOFF_SECONDS: int = 300
    OUTBOX_RETENTION_DAYS: int = 7
    STALE_LOCK_SECONDS: int = 300

    # ---- AI (Ollama) ----
    AI_ENABLED: bool = True
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT_SECONDS: int = 120

    @field_validator("APP_ENV")
    @classmethod
    def _normalise_env(cls, v: str) -> str:
        return (v or "development").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def listen_database_url(self) -> str:
        url = self.DIRECT_DATABASE_URL or self.DATABASE_URL
        # psycopg2.connect() does not understand the SQLAlchemy driver prefix.
        return url.replace("postgresql+psycopg2://", "postgresql://", 1)

    @property
    def email_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_FROM)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    if not settings.JWT_SECRET:
        if settings.is_production:
            raise RuntimeError("JWT_SECRET must be set when APP_ENV=production.")
        # Development convenience: tokens stop working when the process restarts.
        settings.JWT_SECRET = secrets.token_urlsafe(48)
        logger.warning(
            "JWT_SECRET is not set; using a random per-process secret. "
            "Set JWT_SECRET in .env to keep users logged in across restarts."
        )
    elif settings.is_production and len(settings.JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters in production.")

    return settings
