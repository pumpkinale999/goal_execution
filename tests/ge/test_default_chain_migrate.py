"""Default chain migration and sample year structure."""

from __future__ import annotations

from app.constants import (
    DEFAULT_OBJECTIVE_NAME,
    GE_DEFAULT_OBJECTIVE_ID,
    GE_DEFAULT_PROGRAM_ID,
    GE_DEFAULT_SUB_OBJECTIVE_ID,
    SAMPLE_PROGRAM_NAME,
    SAMPLE_PROJECT_NAME,
    SAMPLE_SUB_OBJECTIVE_NAME,
)
from app.services.ge_default_chain_migrate import migrate_default_chain_off_placeholder
from tests.conftest import jwt_headers, service_headers


def _create_dept(client, name: str = "研发部", manager: str = "u-owner") -> str:
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": name, "manager_user_id": manager},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_migrate_default_chain_to_formal_annual(client):
    """Historical fix: move default-chain business content to formal annual root."""
    from app.db import get_session_factory

    year = 2099
    start, end = f"{year}-01-01", f"{year}-12-31"
    dept_id = _create_dept(client)
    client.patch(
        f"/api/v1/ge/objectives/{GE_DEFAULT_OBJECTIVE_ID}",
        headers=service_headers("reviewer-1"),
        json={
            "name": f"{year} 战略",
            "owner_user_id": "u-owner",
            "period_granularity": "year",
            "period_start": start,
            "period_end": end,
        },
    )
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "默认链子目标",
            "parent_id": GE_DEFAULT_OBJECTIVE_ID,
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert sub.status_code == 201, sub.text
    sub_id = sub.json()["id"]

    factory = get_session_factory()
    db = factory()
    try:
        result = migrate_default_chain_off_placeholder(db, actor_user_id="system")
        assert result is not None
        db.commit()
    finally:
        db.close()
    annual_id = result["id"]

    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1")).json()
    b1 = next(o for o in tree if o["id"] == GE_DEFAULT_OBJECTIVE_ID)
    assert b1["name"] == DEFAULT_OBJECTIVE_NAME
    assert b1["owner_user_id"] is None

    annual = next(o for o in tree if o["id"] == annual_id)
    assert annual["name"] == f"{year} 战略"
    moved_sub = next(c for c in annual["children"] if c["id"] == sub_id)
    assert moved_sub["parent_id"] == annual_id


def test_create_year_with_sample_structure(client):
    """Reviewer may attach neutral sample sub/program/project to new annual tree."""
    dept_id = _create_dept(client)
    year = 2098
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1"),
        json={"planning_year": year, "include_sample_structure": True},
    )
    assert resp.status_code == 201, resp.text
    annual_id = resp.json()["id"]

    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1")).json()
    annual = next(o for o in tree if o["id"] == annual_id)
    sample_sub = next(c for c in annual["children"] if c["name"] == SAMPLE_SUB_OBJECTIVE_NAME)
    assert sample_sub["primary_department_id"] == dept_id or sample_sub.get("primary_department_needs_confirmation")
    sample_prog = next(p for p in sample_sub["programs"] if p["name"] == SAMPLE_PROGRAM_NAME)

    projects = client.get("/api/v1/ge/projects", headers=service_headers("reviewer-1")).json()
    sample_project = next(p for p in projects if p["program_id"] == sample_prog["id"])
    assert sample_project["name"] == SAMPLE_PROJECT_NAME

    default_sub = next(
        c for o in tree if o["id"] == GE_DEFAULT_OBJECTIVE_ID for c in o["children"] if c["id"] == GE_DEFAULT_SUB_OBJECTIVE_ID
    )
    assert any(p["id"] == GE_DEFAULT_PROGRAM_ID for p in default_sub["programs"])
