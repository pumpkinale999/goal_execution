"""GE-T250～T254 · ORG-DEPT-GE-VAL-F1 portfolio/migrate without GE org_*."""

from __future__ import annotations

from urllib.parse import urlencode

from tests.conftest import service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_PM,
    U_ZHANGSAN,
    create_project,
    ensure_program_year_period,
)


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": year, "name": f"{year} 年度战略目标"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub_and_program(
    client, company_id: str, dept_id: str, *, owner: str = "910"
) -> tuple[dict, dict]:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("800", is_reviewer=True),
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
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": "专项",
            "objective_id": sub_body["id"],
            "owner_user_id": "911",
            "primary_department_id": dept_id,
        },
    )
    assert prog.status_code == 201, prog.text
    prog_body = prog.json()
    ensure_program_year_period(prog_body["id"])
    return sub_body, prog_body


def _dept_portfolio_url(dept_id: str, *member_ids: str) -> str:
    q = urlencode([("member_user_ids", m) for m in member_ids])
    base = f"/api/v1/ge/portfolios/departments/{dept_id}"
    return f"{base}?{q}" if q else base


def _create_project_on_program(client, program_id: str, *, pm_user_id: str = U_PM, actor: str = "910") -> dict:
    return create_project(
        client,
        actor,
        body={
            **GOLDEN_PROJECT_BODY,
            "program_id": program_id,
            "pm_user_id": pm_user_id,
        },
    )


def test_ge_t250_department_portfolio_opaque_dept_with_injected_members(client):
    """GE-T250: no GE org row; inject members → primary + participation."""
    company = _annual_company(client)
    dept_id = "opaque-dept-product"
    sub, prog = _create_sub_and_program(client, company["id"], dept_id)
    _create_project_on_program(client, prog["id"])

    resp = client.get(
        _dept_portfolio_url(dept_id, U_PM, U_ZHANGSAN),
        headers=service_headers("800", is_reviewer=True),
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


def test_ge_t251_team_portfolio_injected_members(client):
    """GE-T251: team portfolio uses injected members; no primary; no GE org."""
    company = _annual_company(client)
    dept_id = "opaque-dept-eng"
    _sub, prog = _create_sub_and_program(client, company["id"], dept_id, owner=U_PM)
    _create_project_on_program(client, prog["id"], pm_user_id=U_PM, actor=U_PM)

    team_id = "opaque-team-platform"
    q = urlencode([("member_user_ids", U_PM)])
    team_portfolio = client.get(
        f"/api/v1/ge/portfolios/teams/{team_id}?{q}",
        headers=service_headers("800", is_reviewer=True),
    )
    assert team_portfolio.status_code == 200, team_portfolio.text
    assert "primary" not in team_portfolio.json()
    assert any(row["user_id"] == U_PM for row in team_portfolio.json()["accountable"])


def test_ge_t252_migrate_without_org_rows(client):
    """GE-T252: migrate primary ids with no GE org rows."""
    company = _annual_company(client)
    source_id = "opaque-migrate-src"
    target_id = "opaque-migrate-tgt"
    _create_sub_and_program(client, company["id"], source_id)

    migrate = client.post(
        f"/api/v1/ge/portfolios/departments/{source_id}/migrate-primary-objectives",
        headers=service_headers("800", is_reviewer=True),
        json={"target_department_id": target_id},
    )
    assert migrate.status_code == 200, migrate.text
    assert migrate.json()["objectives_migrated"] >= 1

    portfolio = client.get(
        _dept_portfolio_url(target_id),
        headers=service_headers("800", is_reviewer=True),
    )
    assert portfolio.status_code == 200
    assert len(portfolio.json()["primary"]) >= 1


def test_ge_t253_empty_member_user_ids_primary_only(client):
    """GE-T253: omit/empty member_user_ids → primary only, 200."""
    company = _annual_company(client)
    dept_id = "opaque-dept-empty-members"
    sub, prog = _create_sub_and_program(client, company["id"], dept_id)

    resp = client.get(
        f"/api/v1/ge/portfolios/departments/{dept_id}",
        headers=service_headers("800", is_reviewer=True),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    primary_ids = {(row["node_type"], row["node_id"]) for row in body["primary"]}
    assert ("objective", sub["id"]) in primary_ids
    assert ("program", prog["id"]) in primary_ids
    assert body["accountable"] == []
    assert body["contributing"] == []


def test_ge_t254_primary_exact_department_not_subtree(client):
    """GE-T254: child-dept primary does not appear on parent portfolio primary."""
    company = _annual_company(client)
    parent_id = "opaque-parent-dept"
    child_id = "opaque-child-dept"
    _create_sub_and_program(client, company["id"], child_id)

    parent_portfolio = client.get(
        _dept_portfolio_url(parent_id),
        headers=service_headers("800", is_reviewer=True),
    )
    assert parent_portfolio.status_code == 200
    assert parent_portfolio.json()["primary"] == []

    child_portfolio = client.get(
        _dept_portfolio_url(child_id),
        headers=service_headers("800", is_reviewer=True),
    )
    assert child_portfolio.status_code == 200
    assert len(child_portfolio.json()["primary"]) >= 1


def test_user_goal_portfolio_unchanged(client):
    """Regression: user portfolio does not need org or member_user_ids."""
    company = _annual_company(client)
    dept_id = "opaque-user-port"
    sub, prog = _create_sub_and_program(client, company["id"], dept_id, owner=U_PM)
    _create_project_on_program(client, prog["id"], pm_user_id=U_PM, actor=U_PM)

    user_portfolio = client.get(
        f"/api/v1/ge/portfolios/users/{U_PM}",
        headers=service_headers("800", is_reviewer=True),
    )
    assert user_portfolio.status_code == 200
    assert any(row["user_id"] == U_PM for row in user_portfolio.json()["accountable"])
    # DESK-GE1: project items carry program_id/name in one portfolio round-trip.
    pm_row = next(row for row in user_portfolio.json()["accountable"] if row["user_id"] == U_PM)
    project_items = [i for i in pm_row["items"] if i.get("node_type") == "project"]
    assert project_items
    assert project_items[0].get("program_id") == prog["id"]
    assert project_items[0].get("program_name") == prog["name"]
    # DESK-GE1 MS5: objective hang fields (parent_id / level) on owner portfolio.
    obj_items = [i for i in pm_row["items"] if i.get("node_type") == "objective"]
    assert obj_items
    assert any(i.get("parent_id") == company["id"] and i.get("level") == "sub" for i in obj_items)
    # Program hang field objective_id on program owner portfolio.
    owner911 = client.get(
        "/api/v1/ge/portfolios/users/911",
        headers=service_headers("800", is_reviewer=True),
    )
    assert owner911.status_code == 200
    row911 = next(r for r in owner911.json()["accountable"] if r["user_id"] == "911")
    prog_items = [i for i in row911["items"] if i.get("node_type") == "program" and i["node_id"] == prog["id"]]
    assert prog_items
    assert prog_items[0].get("objective_id") == sub["id"]

