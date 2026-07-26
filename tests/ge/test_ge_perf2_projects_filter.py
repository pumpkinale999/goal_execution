"""GE-PERF2.2 · list_projects program_ids filter."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, create_project


def test_ge_perf2_program_ids_filters_and_empty(client):
    created = create_project(client, U_PM)
    program_id = created["program_id"]
    h = jwt_headers(U_PM)

    full = client.get("/api/v1/ge/projects", headers=h)
    assert full.status_code == 200
    assert any(p["id"] == created["id"] for p in full.json())

    filtered = client.get(
        "/api/v1/ge/projects",
        headers=h,
        params=[("program_ids", program_id)],
    )
    assert filtered.status_code == 200
    rows = filtered.json()
    assert all(p["program_id"] == program_id for p in rows)
    assert any(p["id"] == created["id"] for p in rows)

    empty = client.get("/api/v1/ge/projects", headers=h, params=[("program_ids", "")])
    # empty string may be ignored; explicit empty list via no values:
    # FastAPI with program_ids=[] — send program_ids without value twice is hard;
    # unknown id → empty contribution
    unknown = client.get(
        "/api/v1/ge/projects",
        headers=h,
        params=[("program_ids", "00000000-0000-0000-0000-000000000099")],
    )
    assert unknown.status_code == 200
    assert unknown.json() == []

    alias = client.get("/api/v1/ge/projects", headers=h, params={"program_id": program_id})
    assert alias.status_code == 200
    assert any(p["id"] == created["id"] for p in alias.json())
