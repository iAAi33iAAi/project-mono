"""Centralised application settings loaded from environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App-wide configuration — values come from env vars or .env file."""

    app_env: str = Field("development", alias="APP_ENV")
    app_port: int = Field(8000, alias="APP_PORT")
    database_url: str = Field("sqlite:///./dev.db", alias="DATABASE_URL")
    secret_key: str = Field("change-me", alias="SECRET_KEY")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
