"""GE-T131–T132: org charter note id columns and API."""

from __future__ import annotations

from sqlalchemy import inspect

from tests.conftest import jwt_headers, service_headers


def _create_dept(client, name: str = "研发部") -> str:
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": name},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_team(client, dept_id: str, name: str = "前端组") -> str:
    resp = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": name},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_migration_018_note_id_columns(client):
    """GE-T131: department_note_id / team_note_id columns exist."""
    from app.db import get_engine

    inspector = inspect(get_engine())
    dept_cols = {c["name"] for c in inspector.get_columns("org_departments")}
    team_cols = {c["name"] for c in inspector.get_columns("org_teams")}
    assert "department_note_id" in dept_cols
    assert "team_note_id" in team_cols


def test_get_departments_includes_note_ids(client):
    """GE-T132: GET /org/departments returns note id fields (nullable)."""
    dept_id = _create_dept(client)
    team_id = _create_team(client, dept_id)

    resp = client.get("/api/v1/org/departments", headers=jwt_headers("u1"))
    assert resp.status_code == 200
    dept = next(d for d in resp.json() if d["id"] == dept_id)
    assert dept["department_note_id"] is None
    team = next(t for t in dept["teams"] if t["id"] == team_id)
    assert team["team_note_id"] is None


def test_patch_department_binds_note_id(client):
    """GE-T132: PATCH department_note_id persists and reads back."""
    dept_id = _create_dept(client)
    note_id = "550e8400-e29b-41d4-a716-446655440000"

    patch = client.patch(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
        json={"department_note_id": note_id},
    )
    assert patch.status_code == 200
    assert patch.json()["department_note_id"] == note_id

    listed = client.get("/api/v1/org/departments", headers=jwt_headers("u1")).json()
    dept = next(d for d in listed if d["id"] == dept_id)
    assert dept["department_note_id"] == note_id


def test_patch_team_binds_note_id(client):
    """GE-T132: PATCH team_note_id persists and reads back."""
    dept_id = _create_dept(client)
    team_id = _create_team(client, dept_id)
    note_id = "660e8400-e29b-41d4-a716-446655440001"

    patch = client.patch(
        f"/api/v1/org/teams/{team_id}",
        headers=service_headers("reviewer-1"),
        json={"team_note_id": note_id},
    )
    assert patch.status_code == 200
    assert patch.json()["team_note_id"] == note_id

    listed = client.get("/api/v1/org/departments", headers=jwt_headers("u1")).json()
    dept = next(d for d in listed if d["id"] == dept_id)
    team = next(t for t in dept["teams"] if t["id"] == team_id)
    assert team["team_note_id"] == note_id
