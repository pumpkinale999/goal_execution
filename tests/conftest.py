"""Pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ge_db(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.db import init_db, reset_engine_cache

    db_path = tmp_path / "ge.db"
    monkeypatch.setenv("GOAL_EXECUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("GOAL_EXECUTION_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("GOAL_EXECUTION_SERVICE_TOKEN", "test-service-token")
    get_settings.cache_clear()
    reset_engine_cache()
    init_db()
    yield db_path
    get_settings.cache_clear()
    reset_engine_cache()
