"""GE-AUTHZ-T01～T08 · M1 capability matrix (service + actor + is_reviewer)."""

from __future__ import annotations

from tests.conftest import service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_PM,
    U_STRANGER,
    U_ZHANGSAN,
    create_project,
    ensure_formal_test_program,
)

U_GOVERNOR = "u-owner"


def test_ge_authz_t01_stranger_cannot_read_list_or_graph(client):
    created = create_project(client, U_PM)
    listed = client.get("/api/v1/ge/projects", headers=service_headers(U_STRANGER))
    assert listed.status_code == 200
    assert created["id"] not in {p["id"] for p in listed.json()}
    graph = client.get(
        f"/api/v1/ge/projects/{created['id']}/graph",
        headers=service_headers(U_STRANGER),
    )
    assert graph.status_code == 403


def test_ge_authz_t02_participant_pm_governor_can_read(client):
    program_id = ensure_formal_test_program(client, owner_user_id=U_GOVERNOR)
    created = create_project(
        client,
        U_GOVERNOR,
        {**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": U_PM},
    )
    pid = created["id"]
    for uid in (U_ZHANGSAN, U_PM, U_GOVERNOR):
        resp = client.get(f"/api/v1/ge/projects/{pid}/graph", headers=service_headers(uid))
        assert resp.status_code == 200, (uid, resp.text)


def test_ge_authz_t03_reviewer_reads_non_participant_project(client):
    created = create_project(client, U_PM)
    # Must not reuse year creator (reviewer-1 owns company root → goal_subtree_governor).
    pure = "u-pure-reviewer"
    deny = client.get(
        f"/api/v1/ge/projects/{created['id']}/graph",
        headers=service_headers(pure, is_reviewer=False),
    )
    assert deny.status_code == 403
    ok = client.get(
        f"/api/v1/ge/projects/{created['id']}/graph",
        headers=service_headers(pure, is_reviewer=True),
    )
    assert ok.status_code == 200
    listed = client.get("/api/v1/ge/projects", headers=service_headers(pure, is_reviewer=True))
    assert created["id"] in {p["id"] for p in listed.json()}


def test_ge_authz_t04_create_governor_stranger_reviewer(client):
    program_id = ensure_formal_test_program(client, owner_user_id=U_GOVERNOR)
    body = {**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": U_PM}
    ok_gov = client.post("/api/v1/ge/projects", headers=service_headers(U_GOVERNOR), json=body)
    assert ok_gov.status_code == 201, ok_gov.text
    deny = client.post("/api/v1/ge/projects", headers=service_headers(U_STRANGER), json=body)
    assert deny.status_code == 403
    assert deny.json()["detail"] == "not_goal_subtree_governor"
    ok_rev = client.post(
        "/api/v1/ge/projects",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json=body,
    )
    assert ok_rev.status_code == 201, ok_rev.text


def test_ge_authz_t05_force_delete_matrix(client):
    program_id = ensure_formal_test_program(client, owner_user_id=U_GOVERNOR)
    body = {**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": U_ZHANGSAN}
    created = create_project(client, U_GOVERNOR, body)
    pid = created["id"]
    pm_only = client.delete(f"/api/v1/ge/projects/{pid}", headers=service_headers(U_ZHANGSAN))
    assert pm_only.status_code == 409
    assert pm_only.json()["detail"] == "project_not_empty"
    created2 = create_project(client, U_GOVERNOR, body)
    ok_gov = client.delete(
        f"/api/v1/ge/projects/{created2['id']}",
        headers=service_headers(U_GOVERNOR),
    )
    assert ok_gov.status_code == 204
    created3 = create_project(client, U_GOVERNOR, body)
    ok_rev = client.delete(
        f"/api/v1/ge/projects/{created3['id']}",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert ok_rev.status_code == 204


def test_ge_authz_t06_years_assess_role_options_reviewer_only(client):
    stranger = service_headers(U_STRANGER)
    year = client.post(
        "/api/v1/ge/objectives/years",
        headers=stranger,
        json={"planning_year": 2099, "name": "2099 deny"},
    )
    assert year.status_code == 403
    assert year.json()["detail"] == "reviewer_required"
    ok_year = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={"planning_year": 2099, "name": "2099 ok"},
    )
    assert ok_year.status_code == 201, ok_year.text
    company_id = ok_year.json()["id"]
    deny_role = client.post(
        "/api/v1/ge/project-role-options",
        headers=stranger,
        json={"name": "顾问"},
    )
    assert deny_role.status_code == 403
    ok_role = client.post(
        "/api/v1/ge/project-role-options",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={"name": "顾问"},
    )
    assert ok_role.status_code == 201, ok_role.text
    deny_assess = client.post(
        f"/api/v1/ge/objectives/{company_id}/assess",
        headers=stranger,
        json={"lifecycle_status": "completed"},
    )
    assert deny_assess.status_code == 403


def test_ge_authz_t07_governor_check_ignores_reviewer(client):
    program_id = ensure_formal_test_program(client, owner_user_id=U_GOVERNOR)
    # Reviewer header must not make stranger a goal-subtree governor.
    resp = client.get(
        "/api/v1/ge/goal-subtree-governor/check",
        headers=service_headers("reviewer-1", is_reviewer=True),
        params={"user_id": U_STRANGER, "program_id": program_id},
    )
    assert resp.status_code == 200
    assert resp.json()["is_governor"] is False
    ok = client.get(
        "/api/v1/ge/goal-subtree-governor/check",
        headers=service_headers("reviewer-1", is_reviewer=True),
        params={"user_id": U_GOVERNOR, "program_id": program_id},
    )
    assert ok.json()["is_governor"] is True


def test_ge_authz_t08_me_project_access_service_actor(client):
    created = create_project(client, U_PM)
    part = client.get("/api/v1/ge/me/project-access", headers=service_headers(U_PM))
    assert part.status_code == 200
    assert created["id"] in {p["project_id"] for p in part.json()["projects"]}
    stranger = client.get("/api/v1/ge/me/project-access", headers=service_headers(U_STRANGER))
    assert created["id"] not in {p["project_id"] for p in stranger.json()["projects"]}
    rev = client.get(
        "/api/v1/ge/me/project-access?all_visible=1",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert rev.status_code == 200
    assert created["id"] in {p["project_id"] for p in rev.json()["projects"]}
    # all_visible without reviewer must not expand
    no_expand = client.get(
        "/api/v1/ge/me/project-access?all_visible=1",
        headers=service_headers(U_STRANGER, is_reviewer=False),
    )
    assert created["id"] not in {p["project_id"] for p in no_expand.json()["projects"]}
