"""my_related_project_count on GET /ge/objectives program nodes."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import U_PM, U_STRANGER, U_ZHANGSAN, create_project


def _walk_programs(nodes: list[dict]) -> list[dict]:
    out: list[dict] = []
    for node in nodes:
        out.extend(node.get("programs") or [])
        out.extend(_walk_programs(node.get("children") or []))
    return out


def _program_count(tree: list[dict], program_id: str) -> int:
    for prog in _walk_programs(tree):
        if prog["id"] == program_id:
            assert "my_related_project_count" in prog
            return int(prog["my_related_project_count"])
    raise AssertionError(f"program {program_id} not in tree")


def test_related_count_pm_sees_one(client):
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_PM)).json()
    assert _program_count(tree, created["program_id"]) >= 1


def test_related_count_stranger_zero_same_program(client):
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_STRANGER)).json()
    assert _program_count(tree, created["program_id"]) == 0


def test_related_count_assignee_only_not_counted(client):
    """Assignees without roster membership are not 'related' for the badge."""
    created = create_project(client, U_PM)
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_ZHANGSAN)).json()
    # Zhangsan is task assignee on golden project; may or may not be roster member.
    # Assert via members API: if not on roster as non-PM, count must be 0 unless PM.
    members = client.get(
        f"/api/v1/ge/projects/{created['id']}/members",
        headers=jwt_headers(U_PM),
    ).json()["members"]
    on_roster = any(m["user_id"] == U_ZHANGSAN for m in members)
    count = _program_count(tree, created["program_id"])
    if on_roster:
        assert count >= 1
    else:
        assert count == 0


def test_related_count_member_only(client):
    created = create_project(client, U_PM)
    member_uid = "u-badge-member-only"
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
    assert _program_count(tree, created["program_id"]) >= 1


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
    assert _program_count(tree, created["program_id"]) == 0


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
    assert _program_count(tree, created["program_id"]) == 0


def test_related_count_reviewer_uses_participation_not_visibility(client):
    created = create_project(client, U_PM)
    # Reviewer who is not PM/member still gets 0 on this program.
    tree = client.get(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-only", is_reviewer=True),
    ).json()
    assert _program_count(tree, created["program_id"]) == 0
