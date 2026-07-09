"""GE-T11 non-default program validation · P2."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1"),
        json={"planning_year": year},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub(client, company: dict) -> dict:
    company_id = company["id"]
    if company.get("period_start") and company.get("period_end"):
        period_fields = {
            "period_granularity": company.get("period_granularity") or "year",
            "period_start": company["period_start"],
            "period_end": company["period_end"],
        }
    else:
        year = company.get("planning_year", 2026)
        period_fields = {
            "period_granularity": "year",
            "period_start": f"{year}-01-01",
            "period_end": f"{year}-12-31",
        }
    dept = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": "P2部门", "manager_user_id": "u-owner"},
    ).json()
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子目标",
            "parent_id": company_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept["id"],
            **period_fields,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_program_requires_owner_user_id(client):
    company = _annual_company(client)
    sub = _create_sub(client, company)
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "缺 owner", "objective_id": sub["id"]},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "owner_required"


def test_create_program_requires_objective_id(client):
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群", "owner_user_id": "u-owner"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "objective_id_required"


def test_create_objective_requires_owner_user_id(client):
    company = _annual_company(client, year=2027)
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={"name": "子目标", "parent_id": company["id"]},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "owner_required"


def test_jwt_cannot_create_program_directly(client):
    company = _annual_company(client, year=2028)
    sub = _create_sub(client, company)
    resp = client.post(
        "/api/v1/ge/programs",
        headers=jwt_headers("u-owner"),
        json={
            "name": "JWT 禁止",
            "objective_id": sub["id"],
            "owner_user_id": "u-owner",
            "primary_department_id": sub["primary_department_id"],
        },
    )
    assert resp.status_code == 403
