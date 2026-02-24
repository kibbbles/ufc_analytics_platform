"""core/config.py — Application configuration via Pydantic BaseSettings.

Loads environment variables from .env (and the OS environment).
Import `settings` from this module wherever configuration is needed.

Usage:
    from core.config import settings

    db_url = settings.database_url
    if settings.is_production:
        ...
"""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives in the project root (one level above backend/)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = ""

    # Application
    environment: str = "development"
    log_level: str = "DEBUG"

    # CORS — list of allowed origins for the React frontend
    allowed_origins: list[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA fallback
    ]

    @field_validator("log_level", mode="before")
    @classmethod
    def _uppercase_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


# Singleton — import this everywhere
settings = Settings()
