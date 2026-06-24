"""GE-T07 objectives bootstrap tests."""

from __future__ import annotations

from app.constants import (
    DEFAULT_OBJECTIVE_NAME,
    GE_DEFAULT_OBJECTIVE_ID,
    GE_DEFAULT_PROGRAM_ID,
    GE_DEFAULT_SUB_OBJECTIVE_ID,
)
from tests.conftest import jwt_headers


def test_objectives_include_default_chain(client):
    resp = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    data = resp.json()
    assert any(obj["id"] == GE_DEFAULT_OBJECTIVE_ID and obj["name"] == DEFAULT_OBJECTIVE_NAME for obj in data)
    default_obj = next(obj for obj in data if obj["id"] == GE_DEFAULT_OBJECTIVE_ID)
    assert default_obj["programs"] == []
    assert any(child["id"] == GE_DEFAULT_SUB_OBJECTIVE_ID for child in default_obj["children"])
    default_sub = next(child for child in default_obj["children"] if child["id"] == GE_DEFAULT_SUB_OBJECTIVE_ID)
    program_ids = {p["id"] for p in default_sub["programs"]}
    assert GE_DEFAULT_PROGRAM_ID in program_ids
