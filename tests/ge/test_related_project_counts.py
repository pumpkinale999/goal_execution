"""my_visible / my_related project counts on GET /ge/objectives (+ program detail)."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import U_PM, U_STRANGER, U_ZHANGSAN, create_project


def _walk_programs(nodes: list[dict]) -> list[dict]:
    out: list[dict] = []
    for node in nodes:
        out.extend(node.get("programs") or [])
        out.extend(_walk_programs(node.get("children") or []))
    return out


def _program_counts(tree: list[dict], program_id: str) -> tuple[int, int]:
    for prog in _walk_programs(tree):
        if prog["id"] == program_id:
            assert "my_related_project_count" in prog
            assert "my_visible_project_count" in prog
            return int(prog["my_visible_project_count"]), int(prog["my_related_project_count"])
    raise AssertionError(f"program {program_id} not in tree")


def _related_only(tree: list[dict], program_id: str) -> int:
    return _program_counts(tree, program_id)[1]


def test_related_count_pm_sees_one(client):
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_PM)).json()
    visible, related = _program_counts(tree, created["program_id"])
    assert related >= 1
    assert visible == related


def test_related_count_stranger_zero_same_program(client):
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_STRANGER)).json()
    visible, related = _program_counts(tree, created["program_id"])
    assert visible == 0
    assert related == 0


def test_related_count_assignee_only_not_counted(client):
    """Assignees without roster membership are not 'related'; may still be visible."""
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_ZHANGSAN)).json()
    members = client.get(
        f"/api/v1/ge/projects/{created['id']}/members",
        headers=jwt_headers(U_PM),
    ).json()["members"]
    on_roster = any(m["user_id"] == U_ZHANGSAN for m in members)
    visible, related = _program_counts(tree, created["program_id"])
    if on_roster:
        assert related >= 1
        assert visible >= related
    else:
        assert related == 0
        assert visible >= 1  # task assignee ⇒ can_read


def test_related_count_member_only(client):
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
    visible, related = _program_counts(tree, created["program_id"])
    assert related >= 1
    assert visible == related


def test_related_count_cancelled_excluded(client):
    created = create_project(client, U_PM)
    from app.db import get_session_factory
    from app.models.ge import GeProject

    factory = get_session_factory()
    with factory() as db:
        project = db.get(GeProject, created["id"])
        assert project is not None
        project.status = "cancelled"
        db.commit()
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_PM)).json()
    visible, related = _program_counts(tree, created["program_id"])
    assert visible == 0
    assert related == 0


def test_related_count_archived_excluded(client):
    created = create_project(client, U_PM)
    from app.db import get_session_factory
    from app.models.ge import GeProject

    factory = get_session_factory()
    with factory() as db:
        project = db.get(GeProject, created["id"])
        assert project is not None
        project.status = "archived"
        db.commit()
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_PM)).json()
    visible, related = _program_counts(tree, created["program_id"])
    assert visible == 0
    assert related == 0


def test_visible_gt_related_for_reviewer(client):
    """Reviewer sees all effective projects; related stays participation-only."""
    created = create_project(client, U_PM)
    tree = client.get(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-only", is_reviewer=True),
    ).json()
    visible, related = _program_counts(tree, created["program_id"])
    assert related == 0
    assert visible >= 1


def test_related_le_visible_invariant_on_tree(client):
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_PM)).json()
    for prog in _walk_programs(tree):
        visible = int(prog.get("my_visible_project_count") or 0)
        related = int(prog.get("my_related_project_count") or 0)
        assert related <= visible, prog.get("id")


def test_program_detail_exposes_both_counts(client):
    created = create_project(client, U_PM)
    resp = client.get(
        f"/api/v1/ge/programs/{created['program_id']}",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["my_related_project_count"] >= 1
    assert body["my_visible_project_count"] == body["my_related_project_count"]
