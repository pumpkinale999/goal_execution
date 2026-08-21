"""G-PERF-M1 · GET /me/pa-project-roles batch."""

from __future__ import annotations

from app.db import get_session_factory
from app.models.ge import GeProgram
from app.services import ge_goal_subtree_governor
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    TEST_PROJECT_NOTE_ID,
    U_PM,
    U_STRANGER,
    create_project,
)
from tests.ge.test_ge_perf_projects import _seed_program
from tests.ge.test_project_members import _add


def test_pa_project_roles_pm_and_roster(client):
    created = create_project(client, U_PM)
    pid = created["id"]

    resp = client.get("/api/v1/ge/me/pa-project-roles", headers=jwt_headers(U_PM))
    assert resp.status_code == 200, resp.text
    by_id = {p["project_id"]: p for p in resp.json()["projects"]}
    assert pid in by_id
    assert "pm" in by_id[pid]["my_roles"]
    assert by_id[pid]["roster_role"] == "project_manager"

    stranger = client.get("/api/v1/ge/me/pa-project-roles", headers=jwt_headers(U_STRANGER))
    assert stranger.status_code == 200
    assert pid not in {p["project_id"] for p in stranger.json()["projects"]}


def test_pa_project_roles_product_manager_roster(client):
    created = create_project(client, U_PM)
    pid = created["id"]
    uid = "954"
    assert _add(client, pid, uid, "product_manager").status_code == 201

    resp = client.get("/api/v1/ge/me/pa-project-roles", headers=jwt_headers(uid))
    assert resp.status_code == 200, resp.text
    row = next(p for p in resp.json()["projects"] if p["project_id"] == pid)
    assert row["roster_role"] == "product_manager"
    assert "participant" in row["my_roles"]
    assert "pm" not in row["my_roles"]


def test_pa_project_roles_steward_no_roster(client):
    program_id = _seed_program(client, owner="955")
    with get_session_factory()() as db:
        program = db.get(GeProgram, program_id)
        assert program is not None
        program.period_start = "2026-01-01"
        program.period_end = "2026-12-31"
        program.period_granularity = "year"
        db.commit()

    created = create_project(
        client,
        "955",
        body={
            **GOLDEN_PROJECT_BODY,
            "program_id": program_id,
            "pm_user_id": U_PM,
            "project_note_id": TEST_PROJECT_NOTE_ID,
        },
    )
    pid = created["id"]

    resp = client.get("/api/v1/ge/me/pa-project-roles", headers=jwt_headers("955"))
    assert resp.status_code == 200, resp.text
    row = next(p for p in resp.json()["projects"] if p["project_id"] == pid)
    assert "steward" in row["my_roles"]
    assert row["roster_role"] is None


def test_pa_project_roles_alias_match_user_id(client):
    created = create_project(client, U_PM)
    pid = created["id"]
    assert _add(client, pid, "wecom:alias", "product_manager").status_code == 201

    resp = client.get(
        "/api/v1/ge/me/pa-project-roles",
        headers=jwt_headers("wecom:alias"),
        params=[("match_user_id", "wecom:alias"), ("match_user_id", "numeric-twin")],
    )
    assert resp.status_code == 200, resp.text
    row = next(p for p in resp.json()["projects"] if p["project_id"] == pid)
    assert row["roster_role"] == "product_manager"
    assert "participant" in row["my_roles"]


def test_pa_project_roles_no_governor_in_loop(client, monkeypatch):
    create_project(client, U_PM)
    create_project(client, U_PM, body={**GOLDEN_PROJECT_BODY, "name": "第二项目"})

    calls: list[str] = []

    def _spy(**kwargs):
        calls.append(str(kwargs.get("project_id") or kwargs.get("program_id")))
        raise AssertionError("is_goal_subtree_governor must not run in pa-project-roles")

    monkeypatch.setattr(ge_goal_subtree_governor, "is_goal_subtree_governor", _spy)
    monkeypatch.setattr("app.services.ge_access.is_goal_subtree_governor", _spy)

    resp = client.get("/api/v1/ge/me/pa-project-roles", headers=jwt_headers(U_PM))
    assert resp.status_code == 200, resp.text
    assert calls == []
    assert len(resp.json()["projects"]) >= 2
