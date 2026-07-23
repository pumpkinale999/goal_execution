"""GE-T177～T182 · project members roster (M37)."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_STRANGER,
    create_project,
    ensure_formal_test_program,
    get_graph,
    phase_by_name,
    task_id_by_title,
)


U_MEMBER_ONLY = "u-member-only"
U_NEW_ASSIGNEE = "u-new-assignee"


def _members(client, project_id: str, user_id: str = U_PM) -> list[dict]:
    resp = client.get(
        f"/api/v1/ge/projects/{project_id}/members",
        headers=jwt_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["members"]


def _member_by_user(members: list[dict], user_id: str) -> dict:
    for row in members:
        if row["user_id"] == user_id:
            return row
    raise AssertionError(f"user {user_id} not in members: {members}")


def test_ge_t177_create_project_seeds_pm_as_project_manager(client):
    created = create_project(client, U_PM)
    members = _members(client, created["id"])
    pm_row = _member_by_user(members, U_PM)
    assert pm_row["role_slug"] == "project_manager"
    assert pm_row["role_name"] == "项目经理"
    pm_rows = [m for m in members if m["role_slug"] == "project_manager"]
    assert len(pm_rows) == 1


def test_ge_t178_change_pm_replaces_roster_row_and_keeps_assignee_readable(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    # Make old PM also a business-task assignee so they remain participant after roster delete.
    graph = get_graph(client, project_id, U_PM)
    task_id = task_id_by_title(graph, "编写诊断报告")
    patch = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_PM},
    )
    assert patch.status_code == 200, patch.text

    resp = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_PM),
        json={"pm_user_id": U_LISI},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["pm_user_id"] == U_LISI

    members = _members(client, project_id, U_LISI)
    user_ids = {m["user_id"] for m in members}
    assert U_PM not in user_ids
    assert _member_by_user(members, U_LISI)["role_slug"] == "project_manager"

    graph_after = get_graph(client, project_id, U_LISI)
    system_assignees = {
        t["assignee_user_id"]
        for p in graph_after["phases"]
        for t in p["tasks"]
        if t.get("is_system")
    }
    assert U_LISI in system_assignees

    still_readable = client.get(
        f"/api/v1/ge/projects/{project_id}/graph",
        headers=jwt_headers(U_PM),
    )
    assert still_readable.status_code == 200, still_readable.text


def test_ge_t179_roster_only_member_can_read_graph(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    roles = client.get("/api/v1/ge/project-role-options", headers=jwt_headers(U_PM))
    assert roles.status_code == 200
    member_role = next(r for r in roles.json()["role_options"] if r["slug"] == "member")

    add = client.post(
        f"/api/v1/ge/projects/{project_id}/members",
        headers=jwt_headers(U_PM),
        json={"user_id": U_MEMBER_ONLY, "role_option_id": member_role["id"]},
    )
    assert add.status_code == 201, add.text

    ok = client.get(
        f"/api/v1/ge/projects/{project_id}/graph",
        headers=jwt_headers(U_MEMBER_ONLY),
    )
    assert ok.status_code == 200, ok.text

    deny = client.get(
        f"/api/v1/ge/projects/{project_id}/graph",
        headers=jwt_headers(U_STRANGER),
    )
    assert deny.status_code == 403


def test_ge_t180_jwt_cannot_create_role_option_service_can(client):
    deny = client.post(
        "/api/v1/ge/project-role-options",
        headers=jwt_headers(U_PM),
        json={"name": "顾问"},
    )
    assert deny.status_code == 403
    assert deny.json()["detail"] == "reviewer_required"

    created = client.post(
        "/api/v1/ge/project-role-options",
        headers=service_headers("reviewer"),
        json={"name": "顾问", "slug": "advisor"},
    )
    assert created.status_code == 201, created.text
    listed = client.get("/api/v1/ge/project-role-options", headers=jwt_headers(U_PM))
    assert listed.status_code == 200
    names = {r["name"] for r in listed.json()["role_options"]}
    assert "顾问" in names


def test_ge_t181_cannot_delete_current_pm(client):
    created = create_project(client, U_PM)
    resp = client.delete(
        f"/api/v1/ge/projects/{created['id']}/members/{U_PM}",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "cannot_remove_pm"


def test_ge_t182_assignee_upserts_member_without_overwriting_role(client):
    program_id = ensure_formal_test_program(client)
    body = {
        "name": "assignee upsert",
        "pm_user_id": U_PM,
        "program_id": program_id,
        "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
    }
    created = client.post("/api/v1/ge/projects", headers=jwt_headers(U_PM), json=body)
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    graph = get_graph(client, project_id, U_PM)
    phase_id = phase_by_name(graph, "方案")["id"]
    add_task = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks",
        headers=jwt_headers(U_PM),
        json={"title": "新人任务", "assignee_user_id": U_NEW_ASSIGNEE},
    )
    assert add_task.status_code == 200, add_task.text

    members = _members(client, project_id)
    row = _member_by_user(members, U_NEW_ASSIGNEE)
    assert row["role_slug"] == "member"

    roles = client.get("/api/v1/ge/project-role-options", headers=jwt_headers(U_PM)).json()["role_options"]
    advisor = next((r for r in roles if r.get("slug") == "advisor"), None)
    if advisor is None:
        created_role = client.post(
            "/api/v1/ge/project-role-options",
            headers=service_headers("reviewer"),
            json={"name": "顾问", "slug": "advisor"},
        )
        assert created_role.status_code == 201, created_role.text
        advisor = created_role.json()

    patch_role = client.patch(
        f"/api/v1/ge/projects/{project_id}/members/{U_NEW_ASSIGNEE}",
        headers=jwt_headers(U_PM),
        json={"role_option_id": advisor["id"]},
    )
    assert patch_role.status_code == 200, patch_role.text
    assert patch_role.json()["role_slug"] == "advisor"

    task_id = task_id_by_title(get_graph(client, project_id, U_PM), "新人任务")
    reassign = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_NEW_ASSIGNEE},
    )
    assert reassign.status_code == 200, reassign.text
    still = _member_by_user(_members(client, project_id), U_NEW_ASSIGNEE)
    assert still["role_slug"] == "advisor"


def test_members_sorted_by_display_name(client):
    created = create_project(client, U_PM)
    members = _members(client, created["id"])
    names = [m["display_name"] for m in members]
    assert names == sorted(names, key=lambda n: (0, n.casefold()) if n.strip() else (1, ""))
