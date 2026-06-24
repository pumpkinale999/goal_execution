"""ORG-T04–T06: org delete team/department and members list."""

from __future__ import annotations

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


def _assign_profile(client, user_id: str, *, department_id: str | None, team_id: str | None) -> None:
    resp = client.patch(
        f"/api/v1/org/users/{user_id}/profile",
        headers=service_headers("reviewer-1"),
        json={"department_id": department_id, "team_id": team_id},
    )
    assert resp.status_code == 200


def test_patch_team(client):
    dept_id = _create_dept(client)
    team_id = _create_team(client, dept_id)
    resp = client.patch(
        f"/api/v1/org/teams/{team_id}",
        headers=service_headers("reviewer-1"),
        json={"name": "后端组", "lead_user_id": "u-lead"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "后端组"
    assert resp.json()["lead_user_id"] == "u-lead"


def test_delete_team_moves_members_to_unassigned(client):
    dept_id = _create_dept(client)
    team_id = _create_team(client, dept_id)
    _assign_profile(client, "42", department_id=dept_id, team_id=team_id)

    resp = client.delete(
        f"/api/v1/org/teams/{team_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 204

    members = client.get("/api/v1/org/members", headers=service_headers("reviewer-1")).json()
    profile = next(m for m in members if m["user_id"] == "42")
    assert profile["department_id"] is None
    assert profile["team_id"] is None


def test_delete_department_blocked_when_teams_exist(client):
    dept_id = _create_dept(client)
    _create_team(client, dept_id)

    resp = client.delete(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    if isinstance(detail, dict):
        assert detail.get("detail") == "department_has_teams"
    else:
        assert "department_has_teams" in str(detail)


def test_delete_department_when_no_teams(client):
    dept_id = _create_dept(client)
    _assign_profile(client, "7", department_id=dept_id, team_id=None)

    resp = client.delete(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 204

    members = client.get("/api/v1/org/members", headers=service_headers("reviewer-1")).json()
    profile = next(m for m in members if m["user_id"] == "7")
    assert profile["department_id"] is None


def test_list_members_jwt_forbidden(client):
    resp = client.get("/api/v1/org/members", headers=jwt_headers("u1"))
    assert resp.status_code == 403


def test_delete_team_jwt_forbidden(client):
    dept_id = _create_dept(client)
    team_id = _create_team(client, dept_id)
    resp = client.delete(f"/api/v1/org/teams/{team_id}", headers=jwt_headers("u1"))
    assert resp.status_code == 403
