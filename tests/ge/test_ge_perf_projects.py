"""GE-PERF.2 · batch project visibility ACL."""

from __future__ import annotations

from app.services import ge_subtree_governor
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, U_STRANGER, U_ZHANGSAN, bootstrap_startup_gate


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


def _seed_program(client, *, owner: str = "u-owner") -> str:
    company = _annual_company(client)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子目标",
            "parent_id": company["id"],
            "owner_user_id": owner,
            "primary_department_id": dept_id,
        },
    )
    assert sub.status_code == 201, sub.text
    prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "专项",
            "objective_id": sub.json()["id"],
            "owner_user_id": owner,
            "primary_department_id": dept_id,
        },
    )
    assert prog.status_code == 201, prog.text
    return prog.json()["id"]


def _create_project(client, program_id: str, *, pm: str = U_PM, creator: str = "u-owner") -> str:
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(creator),
        json={**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": pm},
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]
    bootstrap_startup_gate(client, pid, creator)
    return pid


def test_ge_perf_04_no_governor_in_list_loop(client, monkeypatch):
    """GE-PERF-04: list_projects must not call is_subtree_governor per project."""
    program_id = _seed_program(client, owner="u-owner")
    _create_project(client, program_id, pm=U_PM, creator="u-owner")
    _create_project(client, program_id, pm=U_ZHANGSAN, creator="u-owner")

    calls: list[str] = []

    def _spy(**kwargs):
        calls.append(str(kwargs.get("project_id") or kwargs.get("program_id")))
        raise AssertionError("is_subtree_governor must not run in list_projects filter loop")

    monkeypatch.setattr(ge_subtree_governor, "is_subtree_governor", _spy)
    monkeypatch.setattr("app.services.ge_access.is_subtree_governor", _spy)

    resp = client.get("/api/v1/ge/projects", headers=jwt_headers("u-owner"))
    assert resp.status_code == 200, resp.text
    assert calls == []
    assert len(resp.json()) >= 2


def test_ge_perf_07_project_visibility_sets(client):
    """GE-PERF-07: PM / governor / stranger visibility sets."""
    program_id = _seed_program(client, owner="u-gov")
    pid = _create_project(client, program_id, pm=U_PM, creator="u-gov")

    as_pm = client.get("/api/v1/ge/projects", headers=jwt_headers(U_PM))
    assert pid in {p["id"] for p in as_pm.json()}

    as_gov = client.get("/api/v1/ge/projects", headers=jwt_headers("u-gov"))
    assert pid in {p["id"] for p in as_gov.json()}

    as_stranger = client.get("/api/v1/ge/projects", headers=jwt_headers(U_STRANGER))
    assert pid not in {p["id"] for p in as_stranger.json()}
