"""GE-T30 · Phase / GateItem planned schedule."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import GOLDEN_PLANNED_DUE, U_PM, create_project, get_graph, phase_by_name


def test_patch_phase_planned_window(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")

    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-30"},
    )
    assert resp.status_code == 200, resp.text
    updated = phase_by_name(resp.json(), "开发")
    assert updated["planned_start"] == "2026-06-01"
    assert updated["planned_end"] == "2026-06-30"


def test_graph_includes_gate_item_planned_due(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = phase_by_name(graph, "方案")["gate_items"][0]
    assert gi["planned_due"] == "2026-06-10"


def test_add_gate_item_requires_planned_due(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")

    missing = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{dev['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "新门控项"},
    )
    assert missing.status_code == 400
    detail = missing.json()["detail"]
    code = detail["detail"] if isinstance(detail, dict) else detail
    assert code == "gate_item_planned_due_required"


def test_gate_item_due_outside_phase_rejected(client):
    body = {
        "name": "排期测试",
        "pm_user_id": U_PM,
        "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
    }
    created = client.post("/api/v1/ge/projects", headers=jwt_headers(U_PM), json=body).json()
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")

    patch = client.patch(
        f"/api/v1/ge/phases/{plan['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-15"},
    )
    assert patch.status_code == 200, patch.text

    resp = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{plan['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "越界门控项", "planned_due": "2026-06-20"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    code = detail["detail"] if isinstance(detail, dict) else detail
    assert code == "gate_item_schedule_outside_phase"


def test_add_gate_item_with_valid_due(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")

    client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-30"},
    )

    resp = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{dev['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "合规门控项", "planned_due": GOLDEN_PLANNED_DUE},
    )
    assert resp.status_code == 200, resp.text
    gi = next(item for item in phase_by_name(resp.json(), "开发")["gate_items"] if item["name"] == "合规门控项")
    assert gi["planned_due"] == GOLDEN_PLANNED_DUE


def test_patch_system_phase_schedule(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    start = graph["phases"][0]
    end = graph["phases"][-1]
    assert start["is_system"] is True
    assert end["name"] == "结束"

    resp = client.patch(
        f"/api/v1/ge/phases/{start['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-01-01", "planned_end": "2026-01-31"},
    )
    assert resp.status_code == 200, resp.text
    updated_start = resp.json()["phases"][0]
    assert updated_start["planned_start"] == "2026-01-01"
    assert updated_start["planned_end"] == "2026-01-31"

    resp_end = client.patch(
        f"/api/v1/ge/phases/{end['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-12-01", "planned_end": "2026-12-31"},
    )
    assert resp_end.status_code == 200, resp_end.text
    updated_end = resp_end.json()["phases"][-1]
    assert updated_end["planned_end"] == "2026-12-31"


def test_business_phase_outside_project_schedule_rejected(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    start = graph["phases"][0]
    end = graph["phases"][-1]
    dev = phase_by_name(graph, "开发")

    client.patch(
        f"/api/v1/ge/phases/{start['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-30"},
    )
    client.patch(
        f"/api/v1/ge/phases/{end['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-09-01", "planned_end": "2026-09-30"},
    )

    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-05-01", "planned_end": "2026-05-31"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    code = detail["detail"] if isinstance(detail, dict) else detail
    assert code == "phase_schedule_outside_project"


def test_patch_task_rejects_schedule_fields(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_id = phase_by_name(graph, "方案")["tasks"][0]["id"]

    resp = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"planned_end": "2026-06-01"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    code = detail["detail"] if isinstance(detail, dict) else detail
    assert code == "unsupported_task_schedule_field"


def test_add_phase_without_window_rejected(client):
    created = create_project(client, U_PM)
    resp = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases",
        headers=jwt_headers(U_PM),
        json={"name": "缺窗口"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "phase_planned_window_required"


def test_patch_business_phase_without_window_rejected(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")

    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"name": "仅改名"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "phase_planned_window_required"
