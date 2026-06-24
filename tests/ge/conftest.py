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


def create_project(
    client: TestClient,
    user_id: str,
    body: dict[str, Any] | None = None,
    *,
    bootstrap_startup: bool = True,
) -> dict[str, Any]:
    payload = dict(body or GOLDEN_PROJECT_BODY)
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
    start_resp = client.post(f"/api/v1/ge/tasks/{start_task_id}/start", headers=jwt_headers(pm_user))
    assert start_resp.status_code == 200, start_resp.text
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
    link = client.post(
        f"/api/v1/ge/tasks/{end_task_id}/start",
        headers=jwt_headers(pm_user),
    )
    assert link.status_code == 200, link.text
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


@pytest.fixture
def golden_active(client):
    return create_project(client, U_PM)
