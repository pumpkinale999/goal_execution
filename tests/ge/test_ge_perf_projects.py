"""GE-PERF.2 · batch project visibility ACL."""

from __future__ import annotations

from app.services import ge_goal_subtree_governor
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, U_STRANGER, U_ZHANGSAN, bootstrap_startup_gate


def _create_dept(client, name: str = "研发部", manager: str = "910") -> str:
    """Opaque dept id — GE org HTTP unmounted; authority lives in skstudio."""
    _ = (client, manager)
    return f"test-dept-{name}"


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": year, "name": f"{year} 年度战略目标"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_program(client, *, owner: str = "910") -> str:
    company = _annual_company(client)
    dept_id = _create_dept(client)
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("800", is_reviewer=True),
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
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": "专项",
            "objective_id": sub.json()["id"],
            "owner_user_id": owner,
            "primary_department_id": dept_id,
        },
    )
    assert prog.status_code == 201, prog.text
    return prog.json()["id"]


def _create_project(client, program_id: str, *, pm: str = U_PM, creator: str = "910") -> str:
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
    """GE-PERF-04: list_projects must not call is_goal_subtree_governor per project."""
    program_id = _seed_program(client, owner="910")
    _create_project(client, program_id, pm=U_PM, creator="910")
    _create_project(client, program_id, pm=U_ZHANGSAN, creator="910")

    calls: list[str] = []

    def _spy(**kwargs):
        calls.append(str(kwargs.get("project_id") or kwargs.get("program_id")))
        raise AssertionError("is_goal_subtree_governor must not run in list_projects filter loop")

    monkeypatch.setattr(ge_goal_subtree_governor, "is_goal_subtree_governor", _spy)
    monkeypatch.setattr("app.services.ge_access.is_goal_subtree_governor", _spy)

    resp = client.get("/api/v1/ge/projects", headers=jwt_headers("910"))
    assert resp.status_code == 200, resp.text
    assert calls == []
    assert len(resp.json()) >= 2


def test_ge_perf_07_project_visibility_sets(client):
    """GE-PERF-07: PM / governor / stranger visibility sets."""
    program_id = _seed_program(client, owner="955")
    pid = _create_project(client, program_id, pm=U_PM, creator="955")

    as_pm = client.get("/api/v1/ge/projects", headers=jwt_headers(U_PM))
    assert pid in {p["id"] for p in as_pm.json()}

    as_gov = client.get("/api/v1/ge/projects", headers=jwt_headers("955"))
    assert pid in {p["id"] for p in as_gov.json()}

    as_stranger = client.get("/api/v1/ge/projects", headers=jwt_headers(U_STRANGER))
    assert pid not in {p["id"] for p in as_stranger.json()}
