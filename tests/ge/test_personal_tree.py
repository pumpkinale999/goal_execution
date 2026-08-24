"""GE-VIS-1 personal left-tree projection (T1–T8, T11–T17 core)."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_PM,
    U_STRANGER,
    U_ZHANGSAN,
    create_project,
    ensure_formal_test_program,
)


U_OWNER = "910"
U_OTHER_OWNER = "920"


def _walk_programs(nodes: list[dict]) -> list[dict]:
    out: list[dict] = []
    for node in nodes:
        out.extend(node.get("programs") or [])
        out.extend(_walk_programs(node.get("children") or []))
    return out


def _walk_objective_ids(nodes: list[dict]) -> set[str]:
    ids: set[str] = set()
    for node in nodes:
        ids.add(node["id"])
        ids |= _walk_objective_ids(node.get("children") or [])
    return ids


def test_t1_stranger_empty_tree(client):
    create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_STRANGER)).json()
    assert tree == []
    assert client.get("/api/v1/ge/programs", headers=jwt_headers(U_STRANGER)).json() == []


def test_t2_roster_member_sees_ancestors_only(client):
    created = create_project(client, U_PM)
    member_uid = "941"
    roles = client.get("/api/v1/ge/project-role-options", headers=jwt_headers(U_PM)).json()[
        "role_options"
    ]
    team = next(r for r in roles if r["slug"] == "member")
    add = client.post(
        f"/api/v1/ge/projects/{created['id']}/members",
        headers=jwt_headers(U_PM),
        json={"user_id": member_uid, "role_option_id": team["id"]},
    )
    assert add.status_code == 201, add.text

    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(member_uid)).json()
    prog_ids = {p["id"] for p in _walk_programs(tree)}
    assert created["program_id"] in prog_ids
    assert len(prog_ids) == 1


def test_t3_program_governor_sees_full_program_including_empty(client):
    program_id = ensure_formal_test_program(client, owner_user_id=U_OWNER)
    empty = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": "空专项留位",
            "objective_id": client.get(
                f"/api/v1/ge/programs/{program_id}", headers=jwt_headers(U_OWNER)
            ).json()["objective_id"],
            "owner_user_id": U_OWNER,
            "primary_department_id": "test-dept-formal",
        },
    )
    assert empty.status_code == 201, empty.text
    empty_id = empty.json()["id"]
    create_project(client, U_OWNER, {**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": U_PM})

    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_OWNER)).json()
    prog_ids = {p["id"] for p in _walk_programs(tree)}
    assert program_id in prog_ids
    assert empty_id in prog_ids

    counts = next(p for p in _walk_programs(tree) if p["id"] == empty_id)
    assert counts["my_visible_project_count"] == 0
    assert counts["my_related_project_count"] == 0


def test_t6_reviewer_full_tree(client):
    created = create_project(client, U_PM)
    tree = client.get(
        "/api/v1/ge/objectives", headers=service_headers("800", is_reviewer=True)
    ).json()
    prog_ids = {p["id"] for p in _walk_programs(tree)}
    assert created["program_id"] in prog_ids
    assert len(_walk_objective_ids(tree)) >= 1


def test_t8_pm_sees_own_program_ancestors(client):
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_PM)).json()
    prog_ids = {p["id"] for p in _walk_programs(tree)}
    assert created["program_id"] in prog_ids


def test_t11_list_projects_no_leak(client):
    created = create_project(client, U_PM)
    hidden = client.get("/api/v1/ge/projects", headers=jwt_headers(U_STRANGER))
    assert created["id"] not in {p["id"] for p in hidden.json()}


def test_t12_t15_programs_list_and_detail(client):
    created = create_project(client, U_PM)
    program_id = created["program_id"]

    listed = client.get("/api/v1/ge/programs", headers=jwt_headers(U_STRANGER)).json()
    assert program_id not in {p["id"] for p in listed}

    as_pm = client.get("/api/v1/ge/programs", headers=jwt_headers(U_PM)).json()
    assert program_id in {p["id"] for p in as_pm}

    denied = client.get(f"/api/v1/ge/programs/{program_id}", headers=jwt_headers(U_STRANGER))
    assert denied.status_code == 404
    assert denied.json()["detail"] == "not_found"


def test_t17_assignee_visible_related_zero(client):
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_ZHANGSAN)).json()
    prog = next(p for p in _walk_programs(tree) if p["id"] == created["program_id"])
    members = client.get(
        f"/api/v1/ge/projects/{created['id']}/members",
        headers=jwt_headers(U_PM),
    ).json()["members"]
    on_roster = any(m["user_id"] == U_ZHANGSAN for m in members)
    if not on_roster:
        assert prog["my_visible_project_count"] >= 1
        assert prog["my_related_project_count"] == 0


def test_t13_list_objectives_no_per_node_governor(client, monkeypatch):
    import app.services.ge_goal_subtree_governor as gov_mod
    import app.services.ge_access as access_mod

    create_project(client, U_PM)

    def _spy(*_a, **_k):
        raise AssertionError("is_goal_subtree_governor must not run in list_objectives path")

    monkeypatch.setattr(gov_mod, "is_goal_subtree_governor", _spy)
    monkeypatch.setattr(access_mod, "is_goal_subtree_governor", _spy)
    resp = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_PM))
    assert resp.status_code == 200
