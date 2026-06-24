"""GET /org/departments tests."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers


def test_list_departments_empty(client):
    resp = client.get("/api/v1/org/departments", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_departments_with_teams(client):
    create = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "研发部", "manager_user_id": "u-mgr"},
    )
    assert create.status_code == 201
    dept_id = create.json()["id"]

    team = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "平台组", "lead_user_id": "u-lead"},
    )
    assert team.status_code == 201

    resp = client.get("/api/v1/org/departments", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "研发部"
    assert data[0]["manager_user_id"] == "u-mgr"
    assert len(data[0]["teams"]) == 1
    assert data[0]["teams"][0]["name"] == "平台组"


def test_departments_requires_auth(client):
    resp = client.get("/api/v1/org/departments")
    assert resp.status_code == 401
