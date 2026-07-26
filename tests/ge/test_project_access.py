"""K27.6 · GET …/project-access batch table."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import U_PM, U_STRANGER, U_ZHANGSAN, create_project
from tests.ge.test_project_members import _add


def test_me_project_access_pm_role_and_visibility(client):
    created = create_project(client, U_PM)
    pid = created["id"]

    resp = client.get("/api/v1/ge/me/project-access", headers=jwt_headers(U_PM))
    assert resp.status_code == 200, resp.text
    by_id = {p["project_id"]: p for p in resp.json()["projects"]}
    assert pid in by_id
    assert by_id[pid]["role"] == "pm"
    assert set(by_id[pid]["doc_singletons"]) == {
        "product_manager",
        "technical_designer",
        "test_designer",
    }

    stranger = client.get("/api/v1/ge/me/project-access", headers=jwt_headers(U_STRANGER))
    assert stranger.status_code == 200
    assert pid not in {p["project_id"] for p in stranger.json()["projects"]}


def test_me_project_access_member_and_singletons(client):
    created = create_project(client, U_PM)
    pid = created["id"]
    assert _add(client, pid, "u-singleton-a", "product_manager").status_code == 201

    resp = client.get("/api/v1/ge/me/project-access", headers=jwt_headers(U_ZHANGSAN))
    assert resp.status_code == 200, resp.text
    row = next(p for p in resp.json()["projects"] if p["project_id"] == pid)
    assert row["role"] == "member"
    assert row["doc_singletons"]["product_manager"] == "u-singleton-a"
    assert row["doc_singletons"]["technical_designer"] == ""


def test_internal_project_access_matches_jwt_visibility(client):
    created = create_project(client, U_PM)
    pid = created["id"]

    jwt_resp = client.get("/api/v1/ge/me/project-access", headers=jwt_headers(U_ZHANGSAN))
    assert jwt_resp.status_code == 200
    internal = client.get(
        f"/api/v1/internal/ge/users/{U_ZHANGSAN}/project-access",
        headers=service_headers("reviewer"),
    )
    assert internal.status_code == 200, internal.text
    assert jwt_resp.json() == internal.json()
    assert pid in {p["project_id"] for p in internal.json()["projects"]}


def test_internal_all_visible_forces_member_role(client):
    created = create_project(client, U_PM)
    pid = created["id"]

    resp = client.get(
        f"/api/v1/internal/ge/users/{U_STRANGER}/project-access",
        headers=service_headers("reviewer"),
        params={"all_visible": "true"},
    )
    assert resp.status_code == 200, resp.text
    by_id = {p["project_id"]: p for p in resp.json()["projects"]}
    assert pid in by_id
    assert by_id[pid]["role"] == "member"


def test_me_project_access_rejects_service_token(client):
    resp = client.get(
        "/api/v1/ge/me/project-access",
        headers=service_headers("reviewer"),
    )
    assert resp.status_code == 403
