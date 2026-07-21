"""ORG-T04–T06 + GE-T119～T130: org memberships and primary."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers


def _create_dept(client, name: str = "研发部") -> str:
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": name},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_team(client, dept_id: str, name: str = "前端组") -> str:
    resp = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": name},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _add_membership(
    client,
    user_id: str,
    *,
    department_id: str,
    team_id: str | None = None,
    primary_membership_id: str | None = None,
) -> dict:
    body: dict = {"department_id": department_id}
    if team_id is not None:
        body["team_id"] = team_id
    if primary_membership_id is not None:
        body["primary_membership_id"] = primary_membership_id
    resp = client.post(
        f"/api/v1/org/users/{user_id}/memberships",
        headers=service_headers("reviewer-1"),
        json=body,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _profile(client, user_id: str) -> dict:
    resp = client.get(
        f"/api/v1/org/users/{user_id}/profile",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_second_department_membership_coexists(client):
    """GE-T119."""
    dept_a = _create_dept(client, "A")
    dept_b = _create_dept(client, "B")
    m1 = _add_membership(client, "u1", department_id=dept_a)
    m2 = client.post(
        "/api/v1/org/users/u1/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_b, "primary_membership_id": m1["id"]},
    )
    assert m2.status_code == 201
    profile = _profile(client, "u1")
    assert len(profile["memberships"]) == 2
    dept_ids = {m["department_id"] for m in profile["memberships"]}
    assert dept_ids == {dept_a, dept_b}


def test_same_department_direct_and_team_coexist(client):
    """GE-T120: direct + team A + team B in same department all kept (v2.36)."""
    dept_id = _create_dept(client)
    team_a = _create_team(client, dept_id, "前端组")
    team_b = _create_team(client, dept_id, "算法组")
    _add_membership(client, "u2", department_id=dept_id)
    resp_a = client.post(
        "/api/v1/org/users/u2/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "team_id": team_a},
    )
    assert resp_a.status_code == 201
    resp_b = client.post(
        "/api/v1/org/users/u2/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "team_id": team_b},
    )
    assert resp_b.status_code == 201, resp_b.text
    profile = _profile(client, "u2")
    assert len(profile["memberships"]) == 3
    assert _dept_membership(profile, dept_id) is not None
    team_ids = {m.get("team_id") for m in profile["memberships"] if m.get("team_id")}
    assert team_ids == {team_a, team_b}


def test_two_teams_same_department_without_direct(client):
    """v2.36: join team A then team B in same dept — no conflict."""
    dept_id = _create_dept(client)
    team_a = _create_team(client, dept_id, "A组")
    team_b = _create_team(client, dept_id, "B组")
    _add_membership(client, "u2b", department_id=dept_id, team_id=team_a)
    resp = client.post(
        "/api/v1/org/users/u2b/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "team_id": team_b},
    )
    assert resp.status_code == 201, resp.text
    profile = _profile(client, "u2b")
    assert len(profile["memberships"]) == 2
    assert {m["team_id"] for m in profile["memberships"]} == {team_a, team_b}


def test_team_then_direct_keeps_team_row(client):
    """v2.36: adding direct after team INSERT keeps team membership."""
    dept_id = _create_dept(client)
    team_id = _create_team(client, dept_id)
    _add_membership(client, "u2c", department_id=dept_id, team_id=team_id)
    resp = client.post(
        "/api/v1/org/users/u2c/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id},
    )
    assert resp.status_code == 201, resp.text
    profile = _profile(client, "u2c")
    assert len(profile["memberships"]) == 2
    assert _dept_membership(profile, dept_id) is not None
    assert any(m.get("team_id") == team_id for m in profile["memberships"])


def _dept_membership(profile: dict, dept_id: str) -> dict | None:
    for m in profile.get("memberships") or []:
        if m.get("department_id") == dept_id and not m.get("team_id"):
            return m
    return None


def test_dept_manager_then_team_lead_keeps_both(client):
    """Anne scenario: dept manager + team lead → 2 memberships, needs primary."""
    dept_id = _create_dept(client, "前端")
    team_id = _create_team(client, dept_id, "1组")
    client.patch(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "anne"},
    )
    profile = _profile(client, "anne")
    assert len(profile["memberships"]) == 1
    assert profile["memberships"][0]["team_id"] is None

    client.patch(
        f"/api/v1/org/teams/{team_id}",
        headers=service_headers("reviewer-1"),
        json={"lead_user_id": "anne"},
    )
    profile = _profile(client, "anne")
    assert len(profile["memberships"]) == 2
    direct = _dept_membership(profile, dept_id)
    assert direct is not None
    assert any(m.get("team_id") == team_id for m in profile["memberships"])
    assert profile["primary_membership_id"] == direct["id"]


def test_manager_append_keeps_other_department(client):
    """GE-T121."""
    dept_a = _create_dept(client, "X")
    dept_b = _create_dept(client, "Y")
    _add_membership(client, "u3", department_id=dept_a)
    client.patch(
        f"/api/v1/org/departments/{dept_b}",
        headers=service_headers("reviewer-1"),
        json={"manager_user_id": "u3"},
    )
    profile = _profile(client, "u3")
    assert len(profile["memberships"]) == 2


def test_delete_department_removes_memberships_only(client):
    """GE-T122."""
    dept_id = _create_dept(client)
    _add_membership(client, "u4", department_id=dept_id)
    resp = client.delete(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 204
    members = client.get("/api/v1/org/members", headers=service_headers("reviewer-1")).json()
    assert not any(m["user_id"] == "u4" for m in members)


def test_get_profile_includes_memberships(client):
    """GE-T123."""
    dept_id = _create_dept(client)
    _add_membership(client, "u5", department_id=dept_id)
    profile = _profile(client, "u5")
    assert len(profile["memberships"]) == 1
    assert profile["memberships"][0]["department_id"] == dept_id


def test_single_membership_auto_primary(client):
    """GE-T126."""
    dept_id = _create_dept(client)
    _add_membership(client, "u6", department_id=dept_id)
    profile = _profile(client, "u6")
    assert profile["primary_membership_id"] == profile["memberships"][0]["id"]
    assert profile["memberships"][0]["is_primary"] is True


def test_patch_primary_membership_validation(client):
    """GE-T127."""
    dept_a = _create_dept(client, "P1")
    dept_b = _create_dept(client, "P2")
    m1 = _add_membership(client, "u7", department_id=dept_a)
    m2 = _add_membership(
        client,
        "u7",
        department_id=dept_b,
        primary_membership_id=m1["id"],
    )
    bad = client.patch(
        "/api/v1/org/users/u7/profile",
        headers=service_headers("reviewer-1"),
        json={"primary_membership_id": "not-a-real-id"},
    )
    assert bad.status_code == 400
    ok = client.patch(
        "/api/v1/org/users/u7/profile",
        headers=service_headers("reviewer-1"),
        json={"primary_membership_id": m2["id"]},
    )
    assert ok.status_code == 200
    assert ok.json()["primary_membership_id"] == m2["id"]


def test_delete_primary_membership_promotes_or_clears(client):
    """GE-T128."""
    dept_a = _create_dept(client, "D1")
    dept_b = _create_dept(client, "D2")
    m1 = _add_membership(client, "u8", department_id=dept_a)
    m2 = _add_membership(
        client,
        "u8",
        department_id=dept_b,
        primary_membership_id=m1["id"],
    )
    client.delete(
        f"/api/v1/org/memberships/{m1['id']}",
        headers=service_headers("reviewer-1"),
    )
    profile = _profile(client, "u8")
    assert len(profile["memberships"]) == 1
    assert profile["primary_membership_id"] == m2["id"]

    client.delete(
        f"/api/v1/org/memberships/{m2['id']}",
        headers=service_headers("reviewer-1"),
    )
    resp = client.get(
        "/api/v1/org/users/u8/profile",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200
    assert resp.json()["memberships"] == []


def test_post_membership_requires_primary_when_multi(client):
    """GE-T130."""
    dept_a = _create_dept(client, "R1")
    dept_b = _create_dept(client, "R2")
    _add_membership(client, "u9", department_id=dept_a)
    profile = _profile(client, "u9")
    assert profile["primary_membership_id"] is not None
    client.patch(
        "/api/v1/org/users/u9/profile",
        headers=service_headers("reviewer-1"),
        json={"primary_membership_id": None},
    )
    resp = client.post(
        "/api/v1/org/users/u9/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_b},
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    if isinstance(detail, dict):
        assert detail.get("detail") == "primary_membership_required"


def test_delete_team_removes_memberships(client):
    dept_id = _create_dept(client)
    team_id = _create_team(client, dept_id)
    _add_membership(client, "42", department_id=dept_id, team_id=team_id)

    resp = client.delete(
        f"/api/v1/org/teams/{team_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 204

    members = client.get("/api/v1/org/members", headers=service_headers("reviewer-1")).json()
    assert not any(m["user_id"] == "42" for m in members)


def test_list_members_jwt_forbidden(client):
    resp = client.get("/api/v1/org/members", headers=jwt_headers("u1"))
    assert resp.status_code == 403
