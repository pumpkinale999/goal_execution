"""GET/PATCH /org/users/{id}/profile access tests (M3: service-token only)."""

from __future__ import annotations

from tests.conftest import raw_user_jwt_headers, service_headers


def test_user_jwt_profile_forbidden(client):
    resp = client.get("/api/v1/org/users/u-self/profile", headers=raw_user_jwt_headers("u-self"))
    assert resp.status_code == 403


def test_service_can_read_any_profile(client):
    patch = client.patch(
        "/api/v1/org/users/u-target/profile",
        headers=service_headers("reviewer-1"),
        json={"proficiency": "senior", "manager_user_id": "u-mgr"},
    )
    assert patch.status_code == 200
    assert patch.json()["user_id"] == "u-target"
    assert patch.json()["proficiency"] == "senior"

    read = client.get(
        "/api/v1/org/users/u-target/profile",
        headers=service_headers("reviewer-1"),
    )
    assert read.status_code == 200
    assert read.json()["proficiency"] == "senior"


def test_service_self_read_after_patch(client):
    client.patch(
        "/api/v1/org/users/u-self/profile",
        headers=service_headers("reviewer-1"),
        json={"proficiency": "mid"},
    )
    resp = client.get("/api/v1/org/users/u-self/profile", headers=service_headers("u-self"))
    assert resp.status_code == 200
    assert resp.json()["proficiency"] == "mid"
