"""GE-AUTHZ-T10 · M2 path consolidation (only /api/v1/ge/*)."""

from __future__ import annotations

from tests.conftest import service_headers
from tests.ge.conftest import U_PM, create_project, ensure_formal_test_program


def test_ge_authz_t10_health_on_ge_prefix(client):
    ok = client.get("/api/v1/ge/health")
    assert ok.status_code == 200
    assert ok.json()["service"] == "goal_execution"
    legacy = client.get("/api/v1/health")
    assert legacy.status_code == 404


def test_ge_authz_t10_governor_check_new_path(client):
    program_id = ensure_formal_test_program(client, owner_user_id=U_PM)
    resp = client.get(
        "/api/v1/ge/goal-subtree-governor/check",
        headers=service_headers("800", is_reviewer=True),
        params={"user_id": U_PM, "program_id": program_id},
    )
    assert resp.status_code == 200
    assert resp.json()["is_governor"] is True
    legacy = client.get(
        "/api/v1/internal/ge/subtree-governor/check",
        headers=service_headers("800", is_reviewer=True),
        params={"user_id": U_PM, "program_id": program_id},
    )
    assert legacy.status_code == 404


def test_ge_authz_t10_user_project_access_and_portfolios(client):
    created = create_project(client, U_PM)
    access = client.get(
        f"/api/v1/ge/users/{U_PM}/project-access",
        headers=service_headers("800", is_reviewer=True),
    )
    assert access.status_code == 200
    assert created["id"] in {p["project_id"] for p in access.json()["projects"]}

    from app.db import get_session_factory
    from app.models.org import OrgDepartment
    from app.services.ge_graph import now_iso

    dept_id = "test-dept-portfolio-m2"
    now = now_iso()
    with get_session_factory()() as db:
        db.add(
            OrgDepartment(
                id=dept_id,
                name="M2 Portfolio",
                manager_user_id=U_PM,
                parent_id=None,
                sort_order=10,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    portfolio = client.get(
        f"/api/v1/ge/portfolios/departments/{dept_id}",
        headers=service_headers("800", is_reviewer=True),
    )
    assert portfolio.status_code == 200, portfolio.text
