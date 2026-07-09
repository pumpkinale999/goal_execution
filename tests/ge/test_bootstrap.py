"""GE-T07: default chain removed in migration 023."""

from __future__ import annotations

from tests.conftest import jwt_headers


def test_objectives_tree_has_no_default_chain(client):
    resp = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    data = resp.json()
    assert not any(obj.get("is_default") for obj in data)
    assert not any(
        child.get("is_default")
        for obj in data
        for child in obj.get("children") or []
    )
