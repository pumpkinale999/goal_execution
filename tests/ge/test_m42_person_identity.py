"""GE-T230～T235 · M42 Person identity hard gate."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import yaml

from app.db import get_session_factory
from app.models.ge import GeAuditEvent
from app.services.ge_graph import record_audit
from app.services.ge_person_id import PERSON_USER_ID_RE
from app.services.ge_queues import build_queues
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_REVIEWER,
    U_ZHANGSAN,
    create_project,
    ensure_formal_test_program,
    get_graph,
    phase_by_name,
)

OPENAPI_PATH = Path(__file__).resolve().parents[3] / "platform-docs" / "openapi" / "ge-v1.yaml"


def _detail(resp) -> str:
    body = resp.json()
    d = body.get("detail", body)
    if isinstance(d, dict):
        return str(d.get("detail") or "")
    return str(d)


def test_ge_t230_patch_assignee_rejects_opaque_and_accepts_digit(client):
    """GE-T230 · wecom:foo → invalid_person_user_id; numeric → 200."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_id = next(t["id"] for phase in graph["phases"] for t in phase["tasks"] if t["title"] == "编写诊断报告")

    bad = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": "wecom:foo"},
    )
    assert bad.status_code == 400
    assert _detail(bad) == "invalid_person_user_id"

    ok = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_LISI},
    )
    assert ok.status_code == 200, ok.text


def test_ge_t231_pm_owner_members_reject_dirty_ids(client):
    """GE-T231 · pm/owner/members non-digit → 400; system assignee → 400."""
    program_id = ensure_formal_test_program(client)

    bad_pm = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(U_PM),
        json={
            "name": "bad pm",
            "pm_user_id": "wecom:pm",
            "program_id": program_id,
            "lifecycle_start": "2026-01-01",
            "lifecycle_end": "2026-12-31",
            "phases": [{"sequence": 1, "name": "P", "gate_items": [], "tasks": []}],
        },
    )
    assert bad_pm.status_code == 400
    assert _detail(bad_pm) == "invalid_person_user_id"

    rev = service_headers(U_REVIEWER, is_reviewer=True)
    year_resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=rev,
        json={"planning_year": 2027, "name": "2027 M42"},
    )
    assert year_resp.status_code == 201, year_resp.text
    company_id = year_resp.json()["id"]
    bad_owner = client.post(
        "/api/v1/ge/objectives",
        headers=rev,
        json={
            "name": "子目标",
            "parent_id": company_id,
            "owner_user_id": "wecom:owner",
            "primary_department_id": "dept-x",
            "period_granularity": "year",
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
        },
    )
    assert bad_owner.status_code == 400
    assert _detail(bad_owner) == "invalid_person_user_id"

    created = create_project(client, U_PM)
    project_id = created["id"]
    from tests.ge.test_project_members import _add, _role

    bad_member = _add(client, project_id, "wecom:member", "member")
    assert bad_member.status_code == 400
    assert _detail(bad_member) == "invalid_person_user_id"

    graph = get_graph(client, project_id, U_PM)
    phase_id = phase_by_name(graph, "方案")["id"]
    bad_system = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks",
        headers=jwt_headers(U_PM),
        json={"title": "系统任务?", "assignee_user_id": "system"},
    )
    assert bad_system.status_code == 400
    assert _detail(bad_system) == "invalid_person_user_id"


def test_ge_t232_audit_system_actor_still_writes(client):
    """GE-T232 · ge_audit_events.actor_user_id=system is not Person-gated."""
    factory = get_session_factory()
    with factory() as db:
        record_audit(
            db,
            actor_user_id="system",
            entity_type="objective",
            entity_id="obj-test",
            action="lifecycle_auto_pending",
            payload={"from": "active", "to": "pending_assessment"},
        )
        db.commit()
        row = db.query(GeAuditEvent).filter(GeAuditEvent.action == "lifecycle_auto_pending").one()
        assert row.actor_user_id == "system"


def test_ge_t233_queue_matches_numeric_assignee_only(client):
    """GE-T233 · queue uses exact assignee == user_id (numeric); username literal no match."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = next(
        gi
        for phase in graph["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == "诊断报告"
    )

    factory = get_session_factory()
    with factory() as db:
        with patch("app.services.ge_queues.today_shanghai", return_value=date(2026, 6, 10)):
            numeric = build_queues(db, U_ZHANGSAN)
            username = build_queues(db, "u-zhangsan")

    numeric_ids = {row["gate_item_id"] for row in numeric["submit"]}
    username_ids = {row["gate_item_id"] for row in username["submit"]}
    assert gi["id"] in numeric_ids
    assert gi["id"] not in username_ids
    assert PERSON_USER_ID_RE.fullmatch(U_ZHANGSAN)
    assert not PERSON_USER_ID_RE.fullmatch("u-zhangsan")


def test_ge_t234_openapi_version_1310():
    """GE-T234 · platform-docs ge-v1.yaml info.version == 1.31.0."""
    if not OPENAPI_PATH.is_file():
        import pytest

        pytest.skip(f"openapi not found at {OPENAPI_PATH}")
    doc = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert doc["info"]["version"] == "1.31.0"


def test_ge_t235_empty_assignee_still_invalid_assignee(client):
    """GE-T235 · empty assignee → invalid_assignee (not invalid_person_user_id)."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_id = next(t["id"] for phase in graph["phases"] for t in phase["tasks"] if t["title"] == "编写诊断报告")

    resp = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": "   "},
    )
    assert resp.status_code == 400
    assert _detail(resp) == "invalid_assignee"
