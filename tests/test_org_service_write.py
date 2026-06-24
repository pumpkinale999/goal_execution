"""Service-token org write tests."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers


def test_create_department_service_only(client):
    resp = client.post(
        "/api/v1/org/departments",
        headers=jwt_headers("u-reviewer"),
        json={"name": "产品部"},
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "产品部", "manager_user_id": "u-pm"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "产品部"
    assert body["manager_user_id"] == "u-pm"
    assert body["teams"] == []


def test_patch_department_and_create_team(client):
    create = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "运营部"},
    )
    dept_id = create.json()["id"]

    patch = client.patch(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
        json={"name": "市场运营部", "manager_user_id": "u-boss"},
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "市场运营部"

    team = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "增长组"},
    )
    assert team.status_code == 201
    assert team.json()["name"] == "增长组"


def test_service_token_without_actor_rejected(client):
    resp = client.post(
        "/api/v1/org/departments",
        headers={"Authorization": "Bearer test-service-token"},
        json={"name": "X"},
    )
    assert resp.status_code == 401
