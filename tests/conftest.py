"""Pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from jose import jwt

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_migrations(db_path: Path) -> None:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")


def jwt_headers(user_id: str, *, secret: str = "test-jwt-secret") -> dict[str, str]:
    token = jwt.encode({"uid": user_id}, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def service_headers(actor_user_id: str, *, token: str = "test-service-token") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Actor-User-Id": actor_user_id,
    }


@pytest.fixture
def ge_db(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.db import reset_engine_cache

    db_path = tmp_path / "ge.db"
    monkeypatch.setenv("GOAL_EXECUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("GOAL_EXECUTION_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("GOAL_EXECUTION_SERVICE_TOKEN", "test-service-token")
    get_settings.cache_clear()
    reset_engine_cache()
    run_migrations(db_path)
    yield db_path
    get_settings.cache_clear()
    reset_engine_cache()


@pytest.fixture
def client(ge_db):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
