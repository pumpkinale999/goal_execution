"""Application settings (GOAL_EXECUTION_*)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    goal_execution_db_path: Path = Path("./data/ge.db")
    goal_execution_jwt_secret: str = ""
    goal_execution_jwt_algorithm: str = "HS256"
    goal_execution_service_token: str = ""
    skstudio_internal_url: str = "http://127.0.0.1:8000"
    host: str = "127.0.0.1"
    port: int = 8092


@lru_cache
def get_settings() -> Settings:
    return Settings()
