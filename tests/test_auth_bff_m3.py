"""M3 AUTH-BFF-01 / PG-01 for goal_execution."""

from __future__ import annotations

import pytest

from tests.conftest import raw_user_jwt_headers, service_headers


def test_auth_bff_01_user_jwt_rejected(client):
    r = client.get("/api/v1/ge/projects", headers=raw_user_jwt_headers("u1"))
    assert r.status_code == 403
    detail = r.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("detail") == "service_token_required"
    else:
        assert "service_token_required" in str(detail)


def test_auth_bff_01_service_token_ok(client):
    r = client.get("/api/v1/ge/projects", headers=service_headers("u1"))
    assert r.status_code == 200


def test_pg01_rejects_sqlite_when_required(monkeypatch):
    from app.config import get_settings
    from app.db import reset_engine_cache, resolve_database_url

    monkeypatch.setenv("REQUIRE_POSTGRES", "1")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/ge-forbid.db")
    get_settings.cache_clear()
    reset_engine_cache()
    with pytest.raises(RuntimeError, match="PG-01"):
        resolve_database_url()
    monkeypatch.delenv("REQUIRE_POSTGRES", raising=False)
    get_settings.cache_clear()
    reset_engine_cache()
