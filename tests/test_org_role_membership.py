"""GE-T114～T118: role appointment syncs user_org_memberships."""

from __future__ import annotations

from tests.conftest import service_headers


def _profile(client, user_id: str) -> dict:
    resp = client.get(
        f"/api/v1/org/users/{user_id}/profile",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _dept_membership(profile: dict, dept_id: str) -> dict | None:
    for m in profile["memberships"]:
        if m["department_id"] == dept_id and m["team_id"] is None:
            return m
    return None


def _team_membership(profile: dict, team_id: str) -> dict | None:
    for m in profile["memberships"]:
        if m["team_id"] == team_id:
            return m
    return None


def test_create_department_with_manager_syncs_profile(client):
    """GE-T114: POST /departments with manager_user_id."""
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "董事会", "manager_user_id": "u-boss"},
    )
    assert resp.status_code == 201
    dept_id = resp.json()["id"]

    profile = _profile(client, "u-boss")
    assert _dept_membership(profile, dept_id) is not None
    assert profile["primary_membership_id"] is not None


def test_patch_department_manager_syncs_profile(client):
    """GE-T115: PATCH /departments/{id} sets manager."""
    create = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "研发部"},
    )
    dept_id = create.json()["id"]

    patch = client.patch(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "u-mgr"},
    )
    assert patch.status_code == 200

    profile = _profile(client, "u-mgr")
    assert _dept_membership(profile, dept_id) is not None


def test_create_and_patch_team_lead_syncs_profile(client):
    """GE-T116: POST/PATCH /teams with lead_user_id."""
    dept = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "平台部"},
    ).json()
    dept_id = dept["id"]

    team = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "后端组", "lead_user_id": "u-lead"},
    )
    assert team.status_code == 201
    team_id = team.json()["id"]

    profile = _profile(client, "u-lead")
    assert _team_membership(profile, team_id) is not None

    team2 = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "前端组"},
    )
    team2_id = team2.json()["id"]

    patch = client.patch(
        f"/api/v1/org/teams/{team2_id}",
        headers=service_headers("reviewer-1"),
        json={"lead_user_id": "u-lead2"},
    )
    assert patch.status_code == 200

    profile2 = _profile(client, "u-lead2")
    assert _team_membership(profile2, team2_id) is not None


def test_clear_manager_or_lead_does_not_change_profile(client):
    """GE-T117: clearing manager/lead leaves membership unchanged."""
    dept = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "运营部", "manager_user_id": "u-mgr"},
    ).json()
    dept_id = dept["id"]

    team = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "增长组", "lead_user_id": "u-lead"},
    ).json()
    team_id = team["id"]

    before_mgr = _profile(client, "u-mgr")
    before_lead = _profile(client, "u-lead")

    client.patch(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": None},
    )
    client.patch(
        f"/api/v1/org/teams/{team_id}",
        headers=service_headers("reviewer-1"),
        json={"lead_user_id": None},
    )

    after_mgr = _profile(client, "u-mgr")
    after_lead = _profile(client, "u-lead")
    assert after_mgr["memberships"] == before_mgr["memberships"]
    assert after_lead["memberships"] == before_lead["memberships"]


def test_cross_department_append_not_override(client):
    """GE-T118: cross-dept append; same-dept group member promoted to dept manager."""
    dept_a = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "A部"},
    ).json()["id"]
    dept_b = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "B部"},
    ).json()["id"]
    team_a = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_a, "name": "A组", "lead_user_id": "u-move"},
    ).json()["id"]

    assert _team_membership(_profile(client, "u-move"), team_a) is not None

    client.patch(
        f"/api/v1/org/departments/{dept_b}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "u-move"},
    )
    moved = _profile(client, "u-move")
    assert _dept_membership(moved, dept_b) is not None
    assert _team_membership(moved, team_a) is not None

    dept_c = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "C部"},
    ).json()["id"]
    team_c = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_c, "name": "C组"},
    ).json()["id"]
    mem = client.post(
        "/api/v1/org/users/u-promote/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_c, "team_id": team_c},
    )
    assert mem.status_code == 201

    client.patch(
        f"/api/v1/org/departments/{dept_c}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "u-promote"},
    )
    promoted = _profile(client, "u-promote")
    assert _dept_membership(promoted, dept_c) is not None
    assert _team_membership(promoted, team_c) is None


def test_replace_manager_only_syncs_new_manager(client):
    dept = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "销售部", "manager_user_id": "u-old"},
    ).json()
    dept_id = dept["id"]

    old_before = _profile(client, "u-old")

    client.patch(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "u-new"},
    )

    assert _profile(client, "u-old")["memberships"] == old_before["memberships"]
    new_profile = _profile(client, "u-new")
    assert _dept_membership(new_profile, dept_id) is not None
