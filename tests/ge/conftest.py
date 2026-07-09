"""GE test fixtures (§12 golden sample)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.constants import (
    SYSTEM_END_GATE_ITEM_NAME,
    SYSTEM_END_SIGN_TASK_TITLE,
    SYSTEM_END_TASK_TITLE,
    SYSTEM_START_GATE_ITEM_NAME,
    SYSTEM_START_TASK_TITLE,
)
from tests.conftest import jwt_headers, service_headers

U_PM = "u-pm"
U_ZHANGSAN = "u-zhangsan"
U_LISI = "u-lisi"
U_WANGWU = "u-wangwu"
U_STRANGER = "u-stranger"
U_CREATOR = "u-creator"

TEST_PROJECT_NOTE_ID = "a0000000-0000-4000-8000-000000000001"

GOLDEN_PLANNED_DUE = "2026-06-15"
DEV_PHASE_PLANNED_DUE = "2026-06-20"

GOLDEN_PROJECT_BODY: dict[str, Any] = {
    "name": "上线 MVP",
    "pm_user_id": U_PM,
    "phases": [
        {
            "sequence": 1,
            "name": "方案",
            "gate_items": [{"key": "X", "name": "诊断报告", "form": "material", "planned_due": "2026-06-10"}],
            "tasks": [
                {
                    "key": "A",
                    "title": "编写诊断报告",
                    "assignee_user_id": U_ZHANGSAN,
                    "produces": ["X"],
                }
            ],
        },
        {
            "sequence": 2,
            "name": "开发",
            "gate_items": [{"key": "Y", "name": "接口规格", "form": "material", "planned_due": "2026-06-20"}],
            "tasks": [
                {
                    "key": "B",
                    "title": "编写接口规格",
                    "assignee_user_id": U_LISI,
                    "produces": ["Y"],
                    "prerequisites": ["X"],
                },
                {
                    "key": "C",
                    "title": "评审接口规格（签收）",
                    "assignee_user_id": U_WANGWU,
                    "prerequisites": ["Y"],
                },
            ],
        },
    ],
}


def material_submit_payload(summary: str, *, project_note_id: str = TEST_PROJECT_NOTE_ID) -> dict[str, Any]:
    return {
        "payload": {
            "summary": summary,
            "content_ref": f"kb:{project_note_id}",
        }
    }


def structured_submit_payload(actual_value: Any, summary: str) -> dict[str, Any]:
    return {
        "payload": {
            "actual_value": actual_value,
            "summary": summary,
        }
    }


def bootstrap_golden_phase_schedule(client: TestClient, project_id: str, user_id: str) -> None:
    """Non-overlapping persisted windows for golden sample (v2.28 adjacency)."""
    graph = get_graph(client, project_id, user_id)
    start = graph["phases"][0]
    end = graph["phases"][-1]
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    patches = [
        (start["id"], {"planned_start": "2026-01-01", "planned_end": "2026-01-07"}),
        (plan["id"], {"planned_start": "2026-06-01", "planned_end": "2026-06-15"}),
        (dev["id"], {"planned_start": "2026-06-16", "planned_end": "2026-06-30"}),
        (end["id"], {"planned_start": "2026-12-01", "planned_end": "2026-12-07"}),
    ]
    for phase_id, body in patches:
        resp = client.patch(
            f"/api/v1/ge/phases/{phase_id}",
            headers=jwt_headers(user_id),
            json=body,
        )
        assert resp.status_code == 200, resp.text


_cached_formal_program_id: str | None = None


@pytest.fixture(autouse=True)
def _reset_formal_program_cache():
    global _cached_formal_program_id
    _cached_formal_program_id = None


def ensure_formal_test_program(
    client: TestClient, *, reviewer: str = "reviewer-1", owner_user_id: str = U_PM
) -> str:
    """Create annual sub + program for tests that create projects (once per test DB)."""
    global _cached_formal_program_id
    if _cached_formal_program_id:
        from app.db import get_session_factory
        from app.models.ge import GeProgram

        with get_session_factory()() as db:
            if db.get(GeProgram, _cached_formal_program_id) is not None:
                return _cached_formal_program_id
        _cached_formal_program_id = None
    year_resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers(reviewer),
        json={"planning_year": 2026},
    )
    assert year_resp.status_code == 201, year_resp.text
    company_id = year_resp.json()["id"]
    dept_resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers(reviewer),
        json={"name": "测试部门", "manager_user_id": owner_user_id},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]
    sub_resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers(reviewer),
        json={
            "name": "测试子目标",
            "parent_id": company_id,
            "owner_user_id": owner_user_id,
            "primary_department_id": dept_id,
            "period_granularity": "year",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert sub_resp.status_code == 201, sub_resp.text
    sub_id = sub_resp.json()["id"]
    prog_resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers(reviewer),
        json={
            "name": "测试专项",
            "objective_id": sub_id,
            "owner_user_id": owner_user_id,
            "primary_department_id": dept_id,
        },
    )
    assert prog_resp.status_code == 201, prog_resp.text
    program_id = prog_resp.json()["id"]
    from app.db import get_session_factory
    from app.models.ge import GeProgram

    factory = get_session_factory()
    with factory() as db:
        program = db.get(GeProgram, program_id)
        assert program is not None
        program.period_start = "2026-01-01"
        program.period_end = "2026-12-31"
        program.period_granularity = "year"
        db.commit()
    _cached_formal_program_id = program_id
    return program_id


def create_project(
    client: TestClient,
    user_id: str,
    body: dict[str, Any] | None = None,
    *,
    bootstrap_startup: bool = True,
    seed_schedule: bool = True,
) -> dict[str, Any]:
    payload = dict(body or GOLDEN_PROJECT_BODY)
    if not payload.get("program_id"):
        payload["program_id"] = ensure_formal_test_program(client)
    if "project_note_id" not in payload:
        payload["project_note_id"] = TEST_PROJECT_NOTE_ID
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(user_id),
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    if bootstrap_startup:
        bootstrap_startup_gate(client, created["id"], user_id)
        if seed_schedule:
            bootstrap_golden_phase_schedule(client, created["id"], user_id)
    return created


def bootstrap_startup_gate(client: TestClient, project_id: str, user_id: str) -> None:
    """Wire sign route and sign 项目启动 so the first business phase can activate."""
    graph = get_graph(client, project_id, user_id)
    pm_user = graph["project"]["pm_user_id"]
    start = phase_by_name(graph, "开始")
    start_gi = next(gi for gi in start["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME)
    start_task_id = task_id_by_title(graph, SYSTEM_START_TASK_TITLE)
    business_phases = [p for p in graph["phases"] if not p.get("is_system")]
    signer_task = None
    for task in start["tasks"]:
        if not task.get("is_system"):
            signer_task = task
            break
    if signer_task is None and business_phases and business_phases[0]["tasks"]:
        signer_task = business_phases[0]["tasks"][0]
    if signer_task is None:
        return
    signer_task_id = signer_task["id"]
    signer_user = signer_task["assignee_user_id"]
    link = client.post(
        f"/api/v1/ge/tasks/{signer_task_id}/prerequisites",
        headers=jwt_headers(pm_user),
        json={"gate_item_id": start_gi["id"]},
    )
    assert link.status_code == 200, link.text
    if start_gi["form"] == "material":
        note_id = graph["project"].get("project_note_id") or TEST_PROJECT_NOTE_ID
        submit_payload = material_submit_payload("项目启动确认", project_note_id=note_id)
    else:
        submit_payload = structured_submit_payload(True, "项目启动确认")
    submit = client.post(
        f"/api/v1/ge/gate-items/{start_gi['id']}/submit",
        headers=jwt_headers(pm_user),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    sign = client.post(
        f"/api/v1/ge/gate-items/{start_gi['id']}/sign",
        headers=jwt_headers(signer_user),
    )
    assert sign.status_code == 200, sign.text


def bootstrap_closure_gate(client: TestClient, project_id: str, user_id: str) -> None:
    """Submit and sign 结项复盘 using auto-seeded PM sign route."""
    graph = get_graph(client, project_id, user_id)
    pm_user = graph["project"]["pm_user_id"]
    end = phase_by_name(graph, "结束")
    end_gi = next(gi for gi in end["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME)
    end_task_id = task_id_by_title(graph, SYSTEM_END_TASK_TITLE)
    signer_user = pm_user
    if end_gi["form"] == "material":
        note_id = graph["project"].get("project_note_id") or TEST_PROJECT_NOTE_ID
        submit_payload = material_submit_payload("结项复盘完成", project_note_id=note_id)
    else:
        submit_payload = structured_submit_payload(True, "结项复盘完成")
    submit = client.post(
        f"/api/v1/ge/gate-items/{end_gi['id']}/submit",
        headers=jwt_headers(pm_user),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    sign = client.post(
        f"/api/v1/ge/gate-items/{end_gi['id']}/sign",
        headers=jwt_headers(signer_user),
    )
    assert sign.status_code == 200, sign.text


def get_graph(client: TestClient, project_id: str, user_id: str) -> dict[str, Any]:
    resp = client.get(
        f"/api/v1/ge/projects/{project_id}/graph",
        headers=jwt_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def phase_by_name(graph: dict[str, Any], name: str) -> dict[str, Any]:
    for phase in graph["phases"]:
        if phase["name"] == name:
            return phase
    raise AssertionError(f"phase {name} not found")


def gate_item_id_by_name(graph: dict[str, Any], name: str) -> str:
    for phase in graph["phases"]:
        for gi in phase["gate_items"]:
            if gi["name"] == name:
                return gi["id"]
    raise AssertionError(f"gate item {name} not found")


def task_id_by_title(graph: dict[str, Any], title: str) -> str:
    for phase in graph["phases"]:
        for task in phase["tasks"]:
            if task["title"] == title:
                return task["id"]
    raise AssertionError(f"task {title} not found")


def overdue_gate_item(graph: dict[str, Any], name: str) -> dict[str, Any]:
    """Return gate item graph node; assert is_overdue when projected."""
    for phase in graph["phases"]:
        for gi in phase["gate_items"]:
            if gi["name"] == name:
                return gi
    raise AssertionError(f"gate item {name} not found")


def open_deviation(
    client: TestClient,
    gate_item_id: str,
    user_id: str,
    *,
    kind: str = "overdue",
) -> dict[str, Any]:
    resp = client.post(
        f"/api/v1/ge/gate-items/{gate_item_id}/deviations/open",
        headers=jwt_headers(user_id),
        json={"kind": kind},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def get_deviation(client: TestClient, deviation_id: str, user_id: str) -> dict[str, Any]:
    resp = client.get(
        f"/api/v1/ge/deviations/{deviation_id}",
        headers=jwt_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture(autouse=True)
def _formal_program_period_for_schedule(ge_db):
    """v2.28 T2: schedule saves require program period on the test program."""
    pass


@pytest.fixture
def golden_active(client):
    return create_project(client, U_PM)


def ensure_program_period(
    client: TestClient,
    program_id: str,
    *,
    period_start: str,
    period_end: str,
    period_granularity: str = "year",
    reviewer: str = "reviewer-1",
) -> dict[str, Any]:
    resp = client.patch(
        f"/api/v1/ge/programs/{program_id}",
        headers=service_headers(reviewer),
        json={
            "period_granularity": period_granularity,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
