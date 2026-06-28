"""Department/team sibling sort_order and reorder API."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers


def _create_department(client, *, name: str, parent_id: str | None = None) -> str:
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": name, "parent_id": parent_id},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_department_list_uses_sort_order(client):
    parent_id = _create_department(client, name="研发部")
    child_b = _create_department(client, name="后端", parent_id=parent_id)
    child_a = _create_department(client, name="前端", parent_id=parent_id)

    down = client.post(
        f"/api/v1/org/departments/{child_a}/reorder",
        headers=service_headers("reviewer-1"),
        json={"direction": "down"},
    )
    assert down.status_code == 200

    resp = client.get("/api/v1/org/departments", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    dept = next(item for item in resp.json() if item["id"] == parent_id)
    child_ids = [item["id"] for item in resp.json() if item.get("parent_id") == parent_id]
    assert child_ids == [child_b, child_a]
    assert dept["teams"] == []


def test_team_reorder_within_department(client):
    dept_id = _create_department(client, name="研发部")
    team_a = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "A组"},
    ).json()["id"]
    team_b = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "B组"},
    ).json()["id"]

    resp = client.post(
        f"/api/v1/org/teams/{team_b}/reorder",
        headers=service_headers("reviewer-1"),
        json={"direction": "up"},
    )
    assert resp.status_code == 200

    listed = client.get("/api/v1/org/departments", headers=jwt_headers("u-1")).json()
    dept = next(item for item in listed if item["id"] == dept_id)
    assert [team["name"] for team in dept["teams"]] == ["B组", "A组"]
    assert team_a == dept["teams"][1]["id"]
