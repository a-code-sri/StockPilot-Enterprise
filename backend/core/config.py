import os
from functools import lru_cache


class Settings:
    """
    Minimal settings loader (no extra deps).
    Set DATABASE_URL in environment, e.g.:
    postgresql+psycopg2://user:pass@host:5432/dbname
    """

    def __init__(self) -> None:
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/app_db",
        )
        self.DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes")


@lru_cache
def get_settings() -> Settings:
    return Settings()