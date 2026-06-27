"""GE-T11 non-default program validation · P2."""

from __future__ import annotations

from app.constants import GE_DEFAULT_SUB_OBJECTIVE_ID
from tests.conftest import jwt_headers, service_headers


def test_create_program_requires_owner_user_id(client):
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "缺 owner", "objective_id": GE_DEFAULT_SUB_OBJECTIVE_ID},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "owner_required"


def test_create_program_requires_objective_id(client):
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群", "owner_user_id": "u-owner"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "objective_id_required"


def test_create_objective_requires_owner_user_id(client):
    from app.constants import GE_DEFAULT_OBJECTIVE_ID

    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={"name": "子目标", "parent_id": GE_DEFAULT_OBJECTIVE_ID},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "owner_required"


def test_jwt_cannot_create_program_directly(client):
    resp = client.post(
        "/api/v1/ge/programs",
        headers=jwt_headers("u-owner"),
        json={
            "name": "JWT 禁止",
            "objective_id": GE_DEFAULT_SUB_OBJECTIVE_ID,
            "owner_user_id": "u-owner",
        },
    )
    assert resp.status_code == 403
