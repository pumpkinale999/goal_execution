"""GE-T114～T118: role appointment syncs user_org_profiles membership."""

from __future__ import annotations

from tests.conftest import service_headers


def _profile(client, user_id: str) -> dict:
    resp = client.get(
        f"/api/v1/org/users/{user_id}/profile",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


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
    assert profile["department_id"] == dept_id
    assert profile["team_id"] is None


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
    assert profile["department_id"] == dept_id
    assert profile["team_id"] is None


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
    assert profile["department_id"] == dept_id
    assert profile["team_id"] == team_id

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
    assert profile2["department_id"] == dept_id
    assert profile2["team_id"] == team2_id


def test_clear_manager_or_lead_does_not_change_profile(client):
    """GE-T117: clearing manager/lead leaves profile unchanged."""
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
    assert after_mgr == before_mgr
    assert after_lead == before_lead


def test_cross_department_and_promote_to_dept_manager(client):
    """GE-T118: cross-dept override; same-dept group member promoted to dept manager."""
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

    assert _profile(client, "u-move")["department_id"] == dept_a
    assert _profile(client, "u-move")["team_id"] == team_a

    client.patch(
        f"/api/v1/org/departments/{dept_b}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "u-move"},
    )
    moved = _profile(client, "u-move")
    assert moved["department_id"] == dept_b
    assert moved["team_id"] is None

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
    client.patch(
        "/api/v1/org/users/u-promote/profile",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_c, "team_id": team_c},
    )

    client.patch(
        f"/api/v1/org/departments/{dept_c}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "u-promote"},
    )
    promoted = _profile(client, "u-promote")
    assert promoted["department_id"] == dept_c
    assert promoted["team_id"] is None


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

    assert _profile(client, "u-old") == old_before
    new_profile = _profile(client, "u-new")
    assert new_profile["department_id"] == dept_id
    assert new_profile["team_id"] is None
