"""GE-PERF.1 · list_objectives one-shot tree + lifecycle TTL."""

from __future__ import annotations

from datetime import date

from sqlalchemy import event

from app.db import get_engine
from app.services import ge_sort_order, ge_strategic_lifecycle
from tests.conftest import jwt_headers, service_headers


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


def _create_sub(client, company_id: str, name: str, dept_id: str) -> str:
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": name,
            "parent_id": company_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_program(client, sub_id: str, name: str, dept_id: str) -> str:
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": name,
            "objective_id": sub_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _seed_tree(client) -> dict[str, str]:
    company = _annual_company(client, year=date.today().year)
    dept_id = _create_dept(client)
    sub_a = _create_sub(client, company["id"], "子目标A", dept_id)
    sub_b = _create_sub(client, company["id"], "子目标B", dept_id)
    prog_a = _create_program(client, sub_a, "项目群A", dept_id)
    prog_b = _create_program(client, sub_b, "项目群B", dept_id)
    return {
        "company_id": company["id"],
        "sub_a": sub_a,
        "sub_b": sub_b,
        "prog_a": prog_a,
        "prog_b": prog_b,
    }


def test_ge_perf_01_no_sibling_queries_and_sql_cap(client, monkeypatch):
    """GE-PERF-01: sibling_* = 0; list-class SELECTs ≤ 3."""
    _seed_tree(client)
    sibling_calls: list[str] = []

    def _spy_obj(db, parent_id):
        sibling_calls.append(f"obj:{parent_id}")
        raise AssertionError("sibling_objectives must not be called")

    def _spy_prog(db, objective_id):
        sibling_calls.append(f"prog:{objective_id}")
        raise AssertionError("sibling_programs must not be called")

    monkeypatch.setattr(ge_sort_order, "sibling_objectives", _spy_obj)
    monkeypatch.setattr(ge_sort_order, "sibling_programs", _spy_prog)

    engine = get_engine()
    statements: list[str] = []

    def _before(conn, cursor, statement, parameters, context, executemany):
        sql = " ".join(str(statement).split()).lower()
        if sql.startswith("select"):
            statements.append(sql)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        ge_strategic_lifecycle.invalidate_lifecycle_refresh()
        resp = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    finally:
        event.remove(engine, "before_cursor_execute", _before)

    assert resp.status_code == 200, resp.text
    assert sibling_calls == []
    assert len(statements) <= 3, statements


def test_ge_perf_03_lifecycle_ttl_skips_second_batch(client, monkeypatch):
    """GE-PERF-03: within TTL, second list does not re-run full batch refresh."""
    _seed_tree(client)
    ge_strategic_lifecycle.invalidate_lifecycle_refresh()

    batch_runs = {"n": 0}
    real_entities = ge_strategic_lifecycle.refresh_lifecycle_entities

    def _counting_entities(db, objectives, programs):
        if ge_strategic_lifecycle._lifecycle_batch_due():
            batch_runs["n"] += 1
        return real_entities(db, objectives, programs)

    monkeypatch.setattr(ge_strategic_lifecycle, "refresh_lifecycle_entities", _counting_entities)
    # routes_ge imported the symbol at load time — patch the route module binding too
    monkeypatch.setattr(
        "app.routes_ge.refresh_lifecycle_entities",
        _counting_entities,
    )

    r1 = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert r1.status_code == 200
    assert batch_runs["n"] == 1

    r2 = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert r2.status_code == 200
    assert batch_runs["n"] == 1
    assert ge_strategic_lifecycle._lifecycle_batch_due() is False


def test_e_perf_ge_01_invalidate_forces_refresh(client, monkeypatch):
    """E-PERF-GE-01: after invalidate / §3.1.1 write, next list batch is due."""
    company = _annual_company(client, year=2020)
    dept_id = _create_dept(client)
    create = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "过期子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "quarter",
            "period_start": "2020-01-01",
            "period_end": "2020-03-31",
        },
    )
    assert create.status_code == 201, create.text
    sub_id = create.json()["id"]

    monkeypatch.setattr(ge_strategic_lifecycle, "today", lambda: date(2020, 4, 1))
    ge_strategic_lifecycle.invalidate_lifecycle_refresh()
    listed = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert listed.status_code == 200

    def _find(nodes, oid):
        for n in nodes:
            if n["id"] == oid:
                return n
            found = _find(n.get("children") or [], oid)
            if found:
                return found
        return None

    sub = _find(listed.json(), sub_id)
    assert sub is not None
    assert sub["lifecycle_status"] == "pending_assessment"

    # Patch name (§3.1.1) must invalidate TTL
    client.patch(
        f"/api/v1/ge/objectives/{sub_id}",
        headers=service_headers("reviewer-1"),
        json={"name": "过期子目标-改"},
    )
    assert ge_strategic_lifecycle._lifecycle_batch_due() is True


def test_ge_perf_07_tree_shape_and_sort(client):
    """GE-PERF-07: tree shape — company → children with programs."""
    ids = _seed_tree(client)
    resp = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    roots = resp.json()
    company = next(r for r in roots if r["id"] == ids["company_id"])
    assert company["level"] == "company"
    assert company["programs"] == []
    child_ids = {c["id"] for c in company["children"]}
    assert ids["sub_a"] in child_ids and ids["sub_b"] in child_ids
    for child in company["children"]:
        prog_ids = {p["id"] for p in child["programs"]}
        if child["id"] == ids["sub_a"]:
            assert ids["prog_a"] in prog_ids
        if child["id"] == ids["sub_b"]:
            assert ids["prog_b"] in prog_ids
