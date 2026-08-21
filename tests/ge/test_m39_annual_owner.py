"""GE-T200 / GE-T201 · M39 annual root owner explicit vs actor fallback."""

from __future__ import annotations

from tests.conftest import service_headers


def test_create_year_explicit_owner_not_actor(client):
    """GE-T200: owner_user_id=U2 (actor≠U2) → owner is U2."""
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={
            "planning_year": 2050,
            "name": "显式负责人根",
            "owner_user_id": "951",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["owner_user_id"] == "951"
    assert body["name"] == "显式负责人根"
    assert body["planning_year"] == 2050


def test_create_year_omitted_or_blank_owner_falls_back_to_actor(client):
    """GE-T201: missing or blank owner_user_id → owner=actor."""
    omitted = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2051, "name": "省略负责人"},
    )
    assert omitted.status_code == 201, omitted.text
    assert omitted.json()["owner_user_id"] == "800"

    blank = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2051, "name": "空白负责人", "owner_user_id": ""},
    )
    assert blank.status_code == 201, blank.text
    assert blank.json()["owner_user_id"] == "800"

    spaces = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2051, "name": "空白格负责人", "owner_user_id": "  "},
    )
    assert spaces.status_code == 201, spaces.text
    assert spaces.json()["owner_user_id"] == "800"
