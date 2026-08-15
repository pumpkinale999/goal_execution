"""GE-T147～T149 · M30 people-summary (program / project)."""

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
    """Opaque dept id — GE org HTTP unmounted; authority lives in skstudio."""
    _ = (client, manager)
    return f"test-dept-{name}"


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={"planning_year": year, "name": f"{year} 年度战略目标"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub_and_program(client, company_id: str, dept_id: str) -> tuple[dict, dict]:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1", is_reviewer=True),
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
        headers=service_headers("reviewer-1", is_reviewer=True),
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


def test_program_and_project_people_summary(client):
    """GE-T147: program and project people-summary."""
    company = _annual_company(client)
    dept_id = _create_dept(client)
    _, prog = _create_sub_and_program(client, company["id"], dept_id)
    project = _create_project_on_program(client, prog["id"])

    prog_resp = client.get(
        f"/api/v1/ge/programs/{prog['id']}/people-summary",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert prog_resp.status_code == 200
    prog_body = prog_resp.json()
    assert any(r["user_id"] == U_PM and r["role"] == "pm" for r in prog_body["accountable"])
    assert any(r["user_id"] == U_ZHANGSAN for r in prog_body["contributing"])
    assert any(r["user_id"] == U_LISI for r in prog_body["contributing"])

    proj_resp = client.get(
        f"/api/v1/ge/projects/{project['id']}/people-summary",
        headers=jwt_headers(U_PM),
    )
    assert proj_resp.status_code == 200
    proj_body = proj_resp.json()
    assert len(proj_body["accountable"]) == 1
    assert proj_body["accountable"][0]["role"] == "pm"
    assert proj_body["accountable"][0]["user_id"] == U_PM


def test_include_completed_filter(client):
    """GE-T149: include_completed hides completed projects by default (program)."""
    from app.db import session_scope
    from app.models.ge import GeProject

    company = _annual_company(client)
    dept_id = _create_dept(client)
    _, prog = _create_sub_and_program(client, company["id"], dept_id)
    project = _create_project_on_program(client, prog["id"])

    with session_scope() as db:
        row = db.get(GeProject, project["id"])
        assert row is not None
        row.status = "completed"
        db.commit()

    hidden = client.get(
        f"/api/v1/ge/programs/{prog['id']}/people-summary",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert hidden.status_code == 200
    pm_accountable = [r for r in hidden.json()["accountable"] if r["user_id"] == U_PM]
    assert pm_accountable == []

    shown = client.get(
        f"/api/v1/ge/programs/{prog['id']}/people-summary?include_completed=1",
        headers=service_headers("reviewer-1", is_reviewer=True),
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
