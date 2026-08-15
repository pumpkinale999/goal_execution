"""PRA §4.11 · GE board-projects for sub-objectives."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, U_STRANGER, bootstrap_startup_gate


def _create_dept() -> str:
    return "test-dept-board"


def _annual_company(client) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={"planning_year": 2026, "name": "2026 年度战略目标"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub_and_programs(client, company_id: str, dept_id: str) -> tuple[dict, dict, dict]:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={
            "name": "看板子目标",
            "parent_id": company_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert sub.status_code == 201, sub.text
    sub_body = sub.json()
    prog_a = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={
            "name": "专项A",
            "objective_id": sub_body["id"],
            "owner_user_id": "u-prog-owner",
            "primary_department_id": dept_id,
        },
    )
    assert prog_a.status_code == 201, prog_a.text
    prog_b = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={
            "name": "专项B空",
            "objective_id": sub_body["id"],
            "owner_user_id": "u-prog-owner",
            "primary_department_id": dept_id,
        },
    )
    assert prog_b.status_code == 201, prog_b.text
    return sub_body, prog_a.json(), prog_b.json()


def _create_project(client, program_id: str, *, name: str = "项目", pm: str = U_PM) -> dict:
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers("u-owner"),
        json={
            **GOLDEN_PROJECT_BODY,
            "name": name,
            "program_id": program_id,
            "pm_user_id": pm,
            "project_note_id": "a0000000-0000-4000-8000-0000000000b1",
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    bootstrap_startup_gate(client, created["id"], "u-owner")
    return created


def test_board_projects_happy_path_includes_empty_program(client):
    company = _annual_company(client)
    dept = _create_dept()
    sub, prog_a, prog_b = _create_sub_and_programs(client, company["id"], dept)
    project = _create_project(client, prog_a["id"], name="可见项目")

    resp = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/board-projects",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["objective_id"] == sub["id"]
    prog_ids = {p["id"] for p in body["programs"]}
    assert prog_a["id"] in prog_ids
    assert prog_b["id"] in prog_ids  # empty program still listed
    assert any(p["id"] == project["id"] for p in body["projects"])
    row = next(p for p in body["projects"] if p["id"] == project["id"])
    assert row["program_id"] == prog_a["id"]
    assert row["lifecycle_status"]
    assert "status" in row


def test_board_projects_company_returns_200_with_subs(client):
    """§4.12: company board-projects → 200 with subs / programs(sub_id) / projects."""
    company = _annual_company(client)
    dept = _create_dept()
    sub, prog_a, prog_b = _create_sub_and_programs(client, company["id"], dept)
    project = _create_project(client, prog_a["id"], name="公司下项目")

    resp = client.get(
        f"/api/v1/ge/objectives/{company['id']}/board-projects",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["objective_id"] == company["id"]
    assert body.get("level") == "company"
    sub_ids = {s["id"] for s in body["subs"]}
    assert sub["id"] in sub_ids
    by_prog = {p["id"]: p for p in body["programs"]}
    assert prog_a["id"] in by_prog
    assert prog_b["id"] in by_prog
    assert by_prog[prog_a["id"]]["sub_objective_id"] == sub["id"]
    assert by_prog[prog_b["id"]]["sub_objective_id"] == sub["id"]
    assert any(p["id"] == project["id"] for p in body["projects"])


def test_board_projects_company_stranger_returns_200_empty_projects(client):
    company = _annual_company(client)
    dept = _create_dept()
    _sub, prog_a, _prog_b = _create_sub_and_programs(client, company["id"], dept)
    _create_project(client, prog_a["id"], name="他人项目")

    resp = client.get(
        f"/api/v1/ge/objectives/{company['id']}/board-projects",
        headers=jwt_headers(U_STRANGER),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["objective_id"] == company["id"]
    assert body["projects"] == []
    assert len(body["subs"]) >= 1
    assert len(body["programs"]) >= 1


def test_board_projects_stranger_returns_200_empty_projects(client):
    """S17: stranger deep-link → 200 + empty projects[] (soft filter, not hard 403)."""
    company = _annual_company(client)
    dept = _create_dept()
    sub, prog_a, prog_b = _create_sub_and_programs(client, company["id"], dept)
    _create_project(client, prog_a["id"], name="他人项目")

    resp = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/board-projects",
        headers=jwt_headers(U_STRANGER),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["objective_id"] == sub["id"]
    prog_ids = {p["id"] for p in body["programs"]}
    assert prog_a["id"] in prog_ids
    assert prog_b["id"] in prog_ids
    assert body["projects"] == []


def test_board_projects_sibling_non_owner_returns_200(client):
    """S13: non-owner under same company still gets 200 (soft entry ACL)."""
    company = _annual_company(client)
    dept = _create_dept()
    sub, prog_a, _prog_b = _create_sub_and_programs(client, company["id"], dept)
    project = _create_project(client, prog_a["id"], name="PM可见", pm=U_PM)

    # Sibling actor owns another sub under the same company but not this one.
    sibling_sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1", is_reviewer=True),
        json={
            "name": "兄弟子目标",
            "parent_id": company["id"],
            "owner_user_id": "u-sibling-owner",
            "primary_department_id": dept,
        },
    )
    assert sibling_sub.status_code == 201, sibling_sub.text

    resp = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/board-projects",
        headers=service_headers("u-sibling-owner", is_reviewer=False),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["objective_id"] == sub["id"]
    # Soft filter: sibling owner is not PM/participant → empty projects
    assert project["id"] not in {p["id"] for p in body["projects"]}

    # PM can still see their project on the same endpoint
    as_pm = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/board-projects",
        headers=service_headers(U_PM, is_reviewer=False),
    )
    assert as_pm.status_code == 200, as_pm.text
    assert any(p["id"] == project["id"] for p in as_pm.json()["projects"])


def test_board_projects_cancelled_still_returned_for_reviewer(client):
    company = _annual_company(client)
    dept = _create_dept()
    sub, prog_a, _prog_b = _create_sub_and_programs(client, company["id"], dept)
    project = _create_project(client, prog_a["id"], name="将取消")

    from app.db import get_session_factory
    from app.models.ge import GeProject

    factory = get_session_factory()
    with factory() as db:
        row = db.get(GeProject, project["id"])
        assert row is not None
        row.status = "cancelled"
        db.commit()

    resp = client.get(
        f"/api/v1/ge/objectives/{sub['id']}/board-projects",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert resp.status_code == 200, resp.text
    rows = {p["id"]: p for p in resp.json()["projects"]}
    assert project["id"] in rows
    assert rows[project["id"]]["lifecycle_status"] == "cancelled"
