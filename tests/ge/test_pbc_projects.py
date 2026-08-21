"""GE PBC projects-for-users: own (PM) ∪ manage (goal-subtree) ∩ period."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, bootstrap_startup_gate


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": year, "name": f"{year} 年度战略目标"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub_program_project(
    client,
    company_id: str,
    *,
    owner: str,
    pm: str,
    period_start: str,
    period_end: str,
    name: str = "专项",
) -> dict:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": "子目标",
            "parent_id": company_id,
            "owner_user_id": owner,
            "primary_department_id": "dept-pbc-proj",
            "period_granularity": "quarter",
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    assert sub.status_code == 201, sub.text
    prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": name,
            "objective_id": sub.json()["id"],
            "owner_user_id": owner,
            "primary_department_id": "dept-pbc-proj",
            "period_granularity": "quarter",
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    assert prog.status_code == 201, prog.text
    created = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(owner),
        json={
            **GOLDEN_PROJECT_BODY,
            "name": f"项目-{name}",
            "program_id": prog.json()["id"],
            "pm_user_id": pm,
            "project_note_id": "a0000000-0000-4000-8000-000000000001",
        },
    )
    assert created.status_code == 201, created.text
    bootstrap_startup_gate(client, created.json()["id"], owner)
    return created.json()


def test_projects_for_users_own_and_manage_in_quarter(client):
    company = _annual_company(client)
    # Q3 window project owned (PM) by U_PM
    own_proj = _create_sub_program_project(
        client,
        company["id"],
        owner="952",
        pm=U_PM,
        period_start="2026-07-01",
        period_end="2026-09-30",
        name="own-prog",
    )
    # Q3 window project managed via objective/program owner
    manage_proj = _create_sub_program_project(
        client,
        company["id"],
        owner=U_PM,
        pm="953",
        period_start="2026-07-01",
        period_end="2026-09-30",
        name="manage-prog",
    )
    # Outside window — must not appear
    _create_sub_program_project(
        client,
        company["id"],
        owner=U_PM,
        pm=U_PM,
        period_start="2026-01-01",
        period_end="2026-03-31",
        name="q1-only",
    )

    resp = client.post(
        "/api/v1/ge/portfolios/projects-for-users",
        headers=service_headers("actor-1"),
        json={
            "user_ids": [U_PM],
            "period_start": "2026-07-01",
            "period_end": "2026-09-30",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_id = {row["project_id"]: row for row in body["projects"]}
    assert own_proj["id"] in by_id
    assert by_id[own_proj["id"]]["relation"] == "own"
    assert manage_proj["id"] in by_id
    assert by_id[manage_proj["id"]]["relation"] == "manage"
    assert len(by_id) == 2


def test_projects_for_users_requires_period(client):
    resp = client.post(
        "/api/v1/ge/portfolios/projects-for-users",
        headers=service_headers("actor-1"),
        json={"user_ids": [U_PM]},
    )
    assert resp.status_code == 400
