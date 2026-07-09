"""GE-T patch project · P2 strategic chain tests."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_CREATOR,
    U_PM,
    create_project,
    ensure_formal_test_program,
)


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1"),
        json={"planning_year": year},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _sub_period_fields(company: dict) -> dict[str, str]:
    if company.get("period_start") and company.get("period_end"):
        return {
            "period_granularity": company.get("period_granularity") or "year",
            "period_start": company["period_start"],
            "period_end": company["period_end"],
        }
    year = company.get("planning_year")
    if year is None and company.get("period_start"):
        year = int(str(company["period_start"])[:4])
    if year is None:
        year = 2026
    return {
        "period_granularity": "year",
        "period_start": f"{year}-01-01",
        "period_end": f"{year}-12-31",
    }


def _create_sub(client, company: dict, name: str = "测试子目标") -> dict:
    company_id = company["id"]
    dept = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": f"{name}部门", "manager_user_id": "u-owner"},
    ).json()
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": name,
            "parent_id": company_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept["id"],
            **_sub_period_fields(company),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_patch_project_name_by_pm(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    resp = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_PM),
        json={"name": "新名称"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名称"


def test_patch_project_forbidden_non_pm(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    resp = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_CREATOR),
        json={"name": "非法"},
    )
    assert resp.status_code == 403


def test_create_program_requires_objective_id(client):
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "objective_id_required"


def test_create_program_on_company_objective_forbidden(client):
    company = _annual_company(client)
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群", "objective_id": company["id"], "owner_user_id": "u-owner"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "program_requires_sub_objective"


def test_create_and_patch_program(client):
    company = _annual_company(client)
    sub = _create_sub(client, company)
    create = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "产品群",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": sub["primary_department_id"],
        },
    )
    assert create.status_code == 201
    program_id = create.json()["id"]
    patch = client.patch(
        f"/api/v1/ge/programs/{program_id}",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群（改）"},
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "产品群（改）"


def test_patch_program_to_company_objective_forbidden(client):
    company = _annual_company(client, year=2027)
    sub = _create_sub(client, company, name="子目标A")
    create = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "产品群",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": sub["primary_department_id"],
            "period_granularity": "quarter",
            "period_start": "2027-01-01",
            "period_end": "2027-03-31",
        },
    )
    assert create.status_code == 201, create.text
    program_id = create.json()["id"]
    resp = client.patch(
        f"/api/v1/ge/programs/{program_id}",
        headers=service_headers("reviewer-1"),
        json={"objective_id": company["id"]},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "program_requires_sub_objective"


def test_create_sub_objective(client):
    company = _annual_company(client, year=2028)
    create = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={"name": "2026 增长", "parent_id": company["id"], "owner_user_id": "u-owner"},
    )
    assert create.status_code == 400
    assert create.json()["detail"] == "primary_department_required"


def test_delete_sub_objective(client):
    company = _annual_company(client, year=2029)
    sub = _create_sub(client, company, name="待删子目标")
    deleted = client.delete(
        f"/api/v1/ge/objectives/{sub['id']}",
        headers=service_headers("reviewer-1"),
    )
    assert deleted.status_code == 204


def test_create_project_requires_explicit_program(client):
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(U_PM),
        json={
            "name": "无专项",
            "pm_user_id": U_PM,
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "program_id_required"


def test_create_project_with_formal_program(client):
    program_id = ensure_formal_test_program(client)
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "program_id": program_id})
    assert created["program_id"] == program_id
