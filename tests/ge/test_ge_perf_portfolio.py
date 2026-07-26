"""ORG-PERF.1 / GE-PERF-05 · set-based goal-portfolio rollup."""

from __future__ import annotations

from sqlalchemy import event

from app.db import get_engine
from app.services import ge_accountability
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, U_ZHANGSAN, bootstrap_startup_gate


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
        json={"planning_year": year, "name": f"{year} 年度战略目标"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub_and_program(client, company_id: str, dept_id: str, *, owner: str) -> tuple[dict, dict]:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": f"子目标-{owner}",
            "parent_id": company_id,
            "owner_user_id": owner,
            "primary_department_id": dept_id,
        },
    )
    assert sub.status_code == 201, sub.text
    prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": f"专项-{owner}",
            "objective_id": sub.json()["id"],
            "owner_user_id": owner,
            "primary_department_id": dept_id,
        },
    )
    assert prog.status_code == 201, prog.text
    return sub.json(), prog.json()


def _membership(client, user_id: str, department_id: str) -> None:
    resp = client.post(
        f"/api/v1/org/users/{user_id}/memberships",
        headers=service_headers("reviewer-1"),
        json={"department_id": department_id},
    )
    assert resp.status_code == 201, resp.text


def _project(client, program_id: str, *, pm: str, creator: str) -> str:
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(creator),
        json={**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": pm},
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]
    bootstrap_startup_gate(client, pid, creator)
    return pid


def test_ge_perf_05_no_per_user_accountable_and_sql_cap(client, monkeypatch):
    """GE-PERF-05: M≥3 members — user_accountable_for_user_id = 0; SELECT ≤ 5."""
    company = _annual_company(client)
    dept_id = _create_dept(client, "产品部")
    users = ["u-a", "u-b", "u-c"]
    for uid in users:
        _membership(client, uid, dept_id)
        _, prog = _create_sub_and_program(client, company["id"], dept_id, owner=uid)
        _project(client, prog["id"], pm=uid, creator=uid)

    calls = {"n": 0}
    real = ge_accountability.user_accountable_for_user_id

    def _spy(db, user_id):
        calls["n"] += 1
        return real(db, user_id)

    monkeypatch.setattr(ge_accountability, "user_accountable_for_user_id", _spy)
    monkeypatch.setattr(
        "app.services.ge_goal_portfolio.user_accountable_for_user_id",
        _spy,
        raising=False,
    )

    engine = get_engine()
    statements: list[str] = []

    def _before(conn, cursor, statement, parameters, context, executemany):
        sql = " ".join(str(statement).split()).lower()
        if sql.startswith("select"):
            statements.append(sql)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        resp = client.get(
            f"/api/v1/org/departments/{dept_id}/goal-portfolio",
            headers=service_headers("reviewer-1"),
        )
    finally:
        event.remove(engine, "before_cursor_execute", _before)

    assert resp.status_code == 200, resp.text
    assert calls["n"] == 0
    assert len(statements) <= 5, statements
    accountable_users = {row["user_id"] for row in resp.json()["accountable"]}
    assert accountable_users >= set(users) or set(users).issubset(accountable_users)


def test_ge_perf_07_portfolio_matches_prior_shape(client):
    """GE-PERF-07: primary + accountable + contributing shape preserved."""
    company = _annual_company(client)
    dept_id = _create_dept(client, "工程部")
    sub, prog = _create_sub_and_program(client, company["id"], dept_id, owner="u-owner")
    _membership(client, U_PM, dept_id)
    _membership(client, U_ZHANGSAN, dept_id)
    _project(client, prog["id"], pm=U_PM, creator="u-owner")

    resp = client.get(
        f"/api/v1/org/departments/{dept_id}/goal-portfolio",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    primary_ids = {(row["node_type"], row["node_id"]) for row in body["primary"]}
    assert ("objective", sub["id"]) in primary_ids
    assert ("program", prog["id"]) in primary_ids
    assert U_PM in {row["user_id"] for row in body["accountable"]}
    assert U_ZHANGSAN in {row["user_id"] for row in body["contributing"]}
