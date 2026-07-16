"""GE-T137～T145 · M29 strategic fields."""

from __future__ import annotations

from datetime import date

from app.services import ge_strategic_lifecycle
from tests.conftest import jwt_headers, service_headers


def _patch_today(monkeypatch, d: date) -> None:
    monkeypatch.setattr(ge_strategic_lifecycle, "today", lambda: d)


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


def test_migration_columns_on_annual_company(client):
    """GE-T137 / GE-T138: strategic columns exist on formal annual roots."""
    company = _annual_company(client)
    assert company["period_granularity"] == "year"
    y = date.today().year
    assert company["period_start"] == f"{y}-01-01"
    assert company["period_end"] == f"{y}-12-31"
    assert company["lifecycle_status"] == "active"
    assert company["is_default"] is False


def test_create_sub_requires_primary_department(client):
    """GE-T139: non-default sub without primary_department_id → 400."""
    company = _annual_company(client)
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子目标无部门",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "primary_department_required"


def test_create_sub_defaults_quarter_period(client):
    """GE-T139: sub without period gets default quarter window."""
    company = _annual_company(client)
    dept_id = _create_dept(client)
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "当季度子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["period_granularity"] == "quarter"
    assert body["period_start"]
    assert body["period_end"]
    assert body["primary_department_id"] == dept_id


def test_period_out_of_parent_bounds(client):
    """GE-T140: child period outside parent company year → 400."""
    company = _annual_company(client, year=2026)
    dept_id = _create_dept(client)
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "越界子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "quarter",
            "period_start": "2025-01-01",
            "period_end": "2025-03-31",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "period_out_of_parent_bounds"


def _find_node(nodes, node_id: str):
    for n in nodes:
        if n["id"] == node_id:
            return n
        found = _find_node(n.get("children") or [], node_id)
        if found:
            return found
    return None


def test_read_refresh_pending_assessment(client, monkeypatch):
    """GE-T141: after period_end, GET moves to pending_assessment."""
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
    assert create.status_code == 201
    sub_id = create.json()["id"]
    _patch_today(monkeypatch, date(2020, 4, 1))
    listed = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert listed.status_code == 200
    sub = _find_node(listed.json(), sub_id)
    assert sub is not None
    assert sub["lifecycle_status"] == "pending_assessment"


def test_locked_objective_allows_owner_patch_rejects_period(client, monkeypatch):
    """Pending/terminal: name+owner patch OK; strategic period patch → 409."""
    company = _annual_company(client, year=2021)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "锁定子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "quarter",
            "period_start": "2021-01-01",
            "period_end": "2021-03-31",
        },
    ).json()
    _patch_today(monkeypatch, date(2021, 4, 2))
    client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))

    ok = client.patch(
        f"/api/v1/ge/objectives/{sub['id']}",
        headers=service_headers("reviewer-1"),
        json={"name": "锁定子目标", "owner_user_id": "anne"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["owner_user_id"] == "anne"

    blocked = client.patch(
        f"/api/v1/ge/objectives/{sub['id']}",
        headers=service_headers("reviewer-1"),
        json={"period_granularity": "quarter", "period_start": "2021-04-01", "period_end": "2021-06-30"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "objective_locked"


def test_assess_objective_and_program(client, monkeypatch):
    """GE-T142 / GE-T142b: assess API for objective and program."""
    company = _annual_company(client, year=2019)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "待评子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "quarter",
            "period_start": "2019-01-01",
            "period_end": "2019-03-31",
        },
    ).json()
    prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "待评专项",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "quarter",
            "period_start": "2019-01-01",
            "period_end": "2019-03-31",
        },
    ).json()
    _patch_today(monkeypatch, date(2019, 4, 1))
    client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))

    obj_assess = client.post(
        f"/api/v1/ge/objectives/{sub['id']}/assess",
        headers=service_headers("reviewer-1"),
        json={"outcome": "met", "note": "ok"},
    )
    assert obj_assess.status_code == 200
    assert obj_assess.json()["lifecycle_status"] == "met"

    prog_assess = client.post(
        f"/api/v1/ge/programs/{prog['id']}/assess",
        headers=service_headers("reviewer-1"),
        json={"outcome": "partial_met"},
    )
    assert prog_assess.status_code == 200
    assert prog_assess.json()["lifecycle_status"] == "partial_met"


def test_delete_program_ignores_soft_deleted_projects(client):
    """Soft-deleted projects must not block program delete (orphan FK allowed)."""
    from tests.ge.conftest import create_project

    company = _annual_company(client)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    ).json()
    prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "空专项",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    ).json()
    created = create_project(
        client,
        "u-owner",
        {
            "name": "临时项目",
            "pm_user_id": "u-owner",
            "program_id": prog["id"],
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
        bootstrap_startup=False,
    )
    assert (
        client.delete(
            f"/api/v1/ge/projects/{created['id']}",
            headers=service_headers("reviewer-1"),
        ).status_code
        == 204
    )
    ok = client.delete(
        f"/api/v1/ge/programs/{prog['id']}",
        headers=service_headers("reviewer-1"),
    )
    assert ok.status_code == 204, ok.text


def test_delete_program_blocked_by_active_project(client):
    from tests.ge.conftest import create_project

    company = _annual_company(client)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子目标2",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    ).json()
    prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "非空专项",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    ).json()
    create_project(
        client,
        "u-owner",
        {
            "name": "仍在的项目",
            "pm_user_id": "u-owner",
            "program_id": prog["id"],
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
        bootstrap_startup=False,
    )
    blocked = client.delete(
        f"/api/v1/ge/programs/{prog['id']}",
        headers=service_headers("reviewer-1"),
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "program_not_empty"


def test_auto_not_met_after_30_days(client, monkeypatch):
    """GE-T143: pending +30d → archived via read refresh."""
    company = _annual_company(client, year=2018)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "超期未评",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "quarter",
            "period_start": "2018-01-01",
            "period_end": "2018-03-31",
        },
    ).json()
    _patch_today(monkeypatch, date(2018, 5, 15))
    client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    listed = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    node = _find_node(listed.json(), sub["id"])
    assert node["lifecycle_status"] == "archived"


def test_create_year_does_not_copy_default_chain(client):
    """GE-T144: years API creates business tree only."""
    first = _annual_company(client, year=2030)
    dept_id = _create_dept(client)
    client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "2030子目标",
            "parent_id": first["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    second = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1"),
        json={"planning_year": 2031, "copy_from_year": 2030},
    )
    assert second.status_code == 201, second.text
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1")).json()
    assert not any(obj.get("is_default") for obj in tree)
    y2031 = second.json()
    assert y2031["planning_year"] == 2031
    assert y2031["is_default"] is False


def test_backfill_script_exists():
    """GE-T145: backfill script is present and importable."""
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "backfill_strategic_fields.py"
    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "--dry-run" in content


def test_create_sub_with_year_granularity(client):
    """GE-T159: sub-objective may use year granularity within parent company year."""
    company = _annual_company(client, year=2026)
    dept_id = _create_dept(client)
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "年度子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "year",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["period_granularity"] == "year"
    assert body["period_start"] == "2026-01-01"
    assert body["period_end"] == "2026-12-31"


def test_create_sub_year_invalid_boundary(client):
    """GE-T159: sub year with non-calendar boundary → 400."""
    company = _annual_company(client, year=2026)
    dept_id = _create_dept(client)
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "非法年度子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "year",
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "period_granularity_invalid"


def test_create_sub_year_out_of_parent_bounds(client):
    """GE-T160: sub year outside parent company window → 400."""
    company = _annual_company(client, year=2026)
    dept_id = _create_dept(client)
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "越界年度子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "year",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "period_out_of_parent_bounds"


def test_create_program_under_year_sub_defaults_quarter(client):
    """GE-T161: program under year sub inherits default quarter, not year."""
    company = _annual_company(client, year=2026)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "年度子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "year",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    ).json()
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "下属专项",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["period_granularity"] == "quarter"
    assert body["period_start"]
    assert body["period_end"]


def test_create_program_with_year_rejected(client):
    """GE-T161: program cannot use year granularity."""
    company = _annual_company(client, year=2026)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "季度子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "quarter",
            "period_start": "2026-04-01",
            "period_end": "2026-06-30",
        },
    ).json()
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "非法专项",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
            "period_granularity": "year",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "period_granularity_invalid"
