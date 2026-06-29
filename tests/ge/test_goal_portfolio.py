"""GE-T151～T154 · M31 goal-portfolio + migrate."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, U_ZHANGSAN, bootstrap_startup_gate


def _create_project_on_program(client, program_id: str, *, pm_user_id: str = U_PM, owner_user_id: str = "u-owner") -> dict:
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(owner_user_id),
        json={
            **GOLDEN_PROJECT_BODY,
            "program_id": program_id,
            "pm_user_id": pm_user_id,
            "project_note_id": "a0000000-0000-4000-8000-000000000001",
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    bootstrap_startup_gate(client, created["id"], owner_user_id)
    return created


def _create_dept(client, name: str, manager: str = "u-owner") -> str:
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


def _create_sub_and_program(client, company_id: str, dept_id: str, *, owner: str = "u-owner") -> tuple[dict, dict]:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子目标",
            "parent_id": company_id,
            "owner_user_id": owner,
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


def _create_membership(client, user_id: str, department_id: str, team_id: str | None = None) -> None:
    resp = client.post(
        f"/api/v1/org/users/{user_id}/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": department_id, "team_id": team_id},
    )
    assert resp.status_code == 201, resp.text


def test_department_goal_portfolio_primary_and_participation(client):
    """GE-T151: department portfolio has primary + participation rollup."""
    company = _annual_company(client)
    dept_id = _create_dept(client, "产品部")
    sub, prog = _create_sub_and_program(client, company["id"], dept_id)
    _create_membership(client, U_PM, dept_id)
    _create_membership(client, U_ZHANGSAN, dept_id)
    _create_project_on_program(client, prog["id"])

    resp = client.get(
        f"/api/v1/org/departments/{dept_id}/goal-portfolio",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    primary_ids = {(row["node_type"], row["node_id"]) for row in body["primary"]}
    assert ("objective", sub["id"]) in primary_ids
    assert ("program", prog["id"]) in primary_ids

    accountable_users = {row["user_id"] for row in body["accountable"]}
    assert U_PM in accountable_users
    contributing_users = {row["user_id"] for row in body["contributing"]}
    assert U_ZHANGSAN in contributing_users


def test_team_and_user_goal_portfolio(client):
    """GE-T152: team has no primary; user portfolio lists accountable + contributing."""
    company = _annual_company(client)
    dept_id = _create_dept(client, "工程部")
    sub, prog = _create_sub_and_program(client, company["id"], dept_id, owner=U_PM)
    team_resp = client.post(
        "/api/v1/org/teams",
        headers=service_headers("reviewer-1"),
        json={"department_id": dept_id, "name": "平台组", "lead_user_id": U_PM},
    )
    assert team_resp.status_code == 201, team_resp.text
    team_id = team_resp.json()["id"]
    _create_membership(client, U_PM, dept_id, team_id)
    _create_project_on_program(client, prog["id"], pm_user_id=U_PM, owner_user_id=U_PM)

    team_portfolio = client.get(
        f"/api/v1/org/teams/{team_id}/goal-portfolio",
        headers=service_headers("reviewer-1"),
    )
    assert team_portfolio.status_code == 200
    assert "primary" not in team_portfolio.json()
    assert any(row["user_id"] == U_PM for row in team_portfolio.json()["accountable"])

    user_portfolio = client.get(
        f"/api/v1/org/users/{U_PM}/goal-portfolio",
        headers=service_headers("reviewer-1"),
    )
    assert user_portfolio.status_code == 200
    user_body = user_portfolio.json()
    assert any(row["user_id"] == U_PM for row in user_body["accountable"])

    zhangsan_portfolio = client.get(
        f"/api/v1/org/users/{U_ZHANGSAN}/goal-portfolio",
        headers=service_headers("reviewer-1"),
    )
    assert zhangsan_portfolio.status_code == 200
    assert any(row["user_id"] == U_ZHANGSAN for row in zhangsan_portfolio.json()["contributing"])


def test_delete_department_blocked_when_primary_objectives(client):
    """GE-T153: DELETE department with primary objectives → 409."""
    company = _annual_company(client)
    dept_id = _create_dept(client, "待删部门")
    _create_sub_and_program(client, company["id"], dept_id)

    resp = client.delete(
        f"/api/v1/org/departments/{dept_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "department_has_primary_objectives"


def test_migrate_then_delete_department(client):
    """GE-T154: migrate primary objectives then DELETE succeeds."""
    company = _annual_company(client)
    source_id = _create_dept(client, "源部门")
    target_id = _create_dept(client, "目标部门")
    _create_sub_and_program(client, company["id"], source_id)

    migrate = client.post(
        f"/api/v1/org/departments/{source_id}/migrate-primary-objectives",
        headers=service_headers("reviewer-1"),
        json={"target_department_id": target_id},
    )
    assert migrate.status_code == 200, migrate.text
    assert migrate.json()["objectives_migrated"] >= 1

    delete = client.delete(
        f"/api/v1/org/departments/{source_id}",
        headers=service_headers("reviewer-1"),
    )
    assert delete.status_code == 204

    portfolio = client.get(
        f"/api/v1/org/departments/{target_id}/goal-portfolio",
        headers=service_headers("reviewer-1"),
    )
    assert portfolio.status_code == 200
    assert len(portfolio.json()["primary"]) >= 1
