"""GE-T146～T149 · M30 people-summary."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_LISI,
    U_PM,
    U_STRANGER,
    U_ZHANGSAN,
    bootstrap_startup_gate,
)


def _create_dept(client, name: str = "研发部", manager: str = "u-owner") -> str:
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": name, "manager_user_id": manager},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1"),
        json={"planning_year": year},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub_and_program(client, company_id: str, dept_id: str) -> tuple[dict, dict]:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子目标",
            "parent_id": company_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert sub.status_code == 201, sub.text
    sub_body = sub.json()
    prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "专项",
            "objective_id": sub_body["id"],
            "owner_user_id": "u-prog-owner",
            "primary_department_id": dept_id,
        },
    )
    assert prog.status_code == 201, prog.text
    return sub_body, prog.json()


def _create_project_on_program(client, program_id: str, *, pm_user_id: str = U_PM) -> dict:
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers("u-owner"),
        json={
            **GOLDEN_PROJECT_BODY,
            "program_id": program_id,
            "pm_user_id": pm_user_id,
            "project_note_id": "a0000000-0000-4000-8000-000000000001",
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    bootstrap_startup_gate(client, created["id"], "u-owner")
    return created


def test_objective_people_summary_accountable_and_contributing(client):
    """GE-T146: objective people-summary splits accountable vs contributing."""
    company = _annual_company(client)
    dept_id = _create_dept(client)
    sub, prog = _create_sub_and_program(client, company["id"], dept_id)
    project = _create_project_on_program(client, prog["id"])

    resp = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/people-summary",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["include_completed"] is False

    accountable_users = {row["user_id"] for row in body["accountable"]}
    assert "u-owner" in accountable_users
    assert "u-prog-owner" in accountable_users
    assert U_PM in accountable_users

    contributing = {row["user_id"]: row for row in body["contributing"]}
    assert U_ZHANGSAN in contributing
    assert U_LISI in contributing
    assert U_PM not in contributing
    assert contributing[U_ZHANGSAN]["projects"][0]["project_id"] == project["id"]
    assert contributing[U_ZHANGSAN]["projects"][0]["task_count"] >= 1


def test_program_and_project_people_summary(client):
    """GE-T147: program and project people-summary."""
    company = _annual_company(client)
    dept_id = _create_dept(client)
    _, prog = _create_sub_and_program(client, company["id"], dept_id)
    project = _create_project_on_program(client, prog["id"])

    prog_resp = client.get(
        f"/api/v1/ge/programs/{prog['id']}/people-summary",
        headers=service_headers("reviewer-1"),
    )
    assert prog_resp.status_code == 200
    prog_body = prog_resp.json()
    assert any(r["user_id"] == U_PM and r["role"] == "pm" for r in prog_body["accountable"])
    assert any(r["user_id"] == U_ZHANGSAN for r in prog_body["contributing"])

    proj_resp = client.get(
        f"/api/v1/ge/projects/{project['id']}/people-summary",
        headers=jwt_headers(U_PM),
    )
    assert proj_resp.status_code == 200
    proj_body = proj_resp.json()
    assert len(proj_body["accountable"]) == 1
    assert proj_body["accountable"][0]["role"] == "pm"
    assert proj_body["accountable"][0]["user_id"] == U_PM


def test_assignee_rollup_to_ancestor_objective(client):
    """GE-T148: assignee appears in ancestor objective contributing rollup."""
    company = _annual_company(client)
    dept_id = _create_dept(client)
    sub, prog = _create_sub_and_program(client, company["id"], dept_id)
    _create_project_on_program(client, prog["id"])

    resp = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/people-summary",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200
    contributing_users = {row["user_id"] for row in resp.json()["contributing"]}
    assert U_ZHANGSAN in contributing_users


def test_include_completed_filter(client):
    """GE-T149: include_completed hides completed projects by default."""
    from app.db import session_scope
    from app.models.ge import GeProject

    company = _annual_company(client)
    dept_id = _create_dept(client)
    sub, prog = _create_sub_and_program(client, company["id"], dept_id)
    project = _create_project_on_program(client, prog["id"])

    with session_scope() as db:
        row = db.get(GeProject, project["id"])
        assert row is not None
        row.status = "completed"
        db.commit()

    hidden = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/people-summary",
        headers=service_headers("reviewer-1"),
    )
    assert hidden.status_code == 200
    pm_accountable = [r for r in hidden.json()["accountable"] if r["user_id"] == U_PM]
    assert pm_accountable == []

    shown = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/people-summary?include_completed=1",
        headers=service_headers("reviewer-1"),
    )
    assert shown.status_code == 200
    pm_accountable = [r for r in shown.json()["accountable"] if r["user_id"] == U_PM]
    assert len(pm_accountable) == 1


def test_project_people_summary_forbidden_for_stranger(client):
    company = _annual_company(client)
    dept_id = _create_dept(client)
    _, prog = _create_sub_and_program(client, company["id"], dept_id)
    project = _create_project_on_program(client, prog["id"])

    resp = client.get(
        f"/api/v1/ge/projects/{project['id']}/people-summary",
        headers=jwt_headers(U_STRANGER),
    )
    assert resp.status_code == 403
