"""Graph edit link API tests."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import (
    GOLDEN_PLANNED_DUE,
    U_PM,
    create_project,
    ensure_formal_test_program,
    phase_by_name,
    task_id_by_title,
)


def _create_empty_draft(client):
    program_id = ensure_formal_test_program(client)
    body = {
        "name": "连线测试",
        "pm_user_id": U_PM,
        "program_id": program_id,
        "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
    }
    resp = client.post("/api/v1/ge/projects", headers=jwt_headers(U_PM), json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_add_task_requires_assignee(client):
    project_id = _create_empty_draft(client)
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    phase_id = phase_by_name(graph, "方案")["id"]
    url = f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks"

    missing = client.post(url, headers=jwt_headers(U_PM), json={"title": "无负责人"})
    assert missing.status_code == 400
    assert missing.json()["detail"] == "invalid_assignee"

    empty = client.post(
        url,
        headers=jwt_headers(U_PM),
        json={"title": "空负责人", "assignee_user_id": "   "},
    )
    assert empty.status_code == 400
    assert empty.json()["detail"] == "invalid_assignee"


def test_add_task_rejects_empty_title(client):
    project_id = _create_empty_draft(client)
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    phase_id = phase_by_name(graph, "方案")["id"]
    url = f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks"

    resp = client.post(
        url,
        headers=jwt_headers(U_PM),
        json={"title": "   ", "assignee_user_id": U_PM},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_request"


def test_add_gate_item_rejects_empty_name(client):
    project_id = _create_empty_draft(client)
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    phase_id = phase_by_name(graph, "方案")["id"]
    url = f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/gate-items"

    resp = client.post(
        url,
        headers=jwt_headers(U_PM),
        json={"name": "   ", "planned_due": GOLDEN_PLANNED_DUE},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_request"


def test_mouse_link_flow(client):
    project_id = _create_empty_draft(client)
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    assert graph["graph_editable"] is True
    phase_id = phase_by_name(graph, "方案")["id"]

    task = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks",
        headers=jwt_headers(U_PM),
        json={"title": "编写报告", "assignee_user_id": U_PM},
    )
    assert task.status_code == 200
    plan = phase_by_name(task.json(), "方案")
    task_id = plan["tasks"][0]["id"]

    gate = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "诊断报告", "planned_due": GOLDEN_PLANNED_DUE},
    )
    assert gate.status_code == 200
    gate_item_id = phase_by_name(gate.json(), "方案")["gate_items"][0]["id"]

    sign_task = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks",
        headers=jwt_headers(U_PM),
        json={"title": "评审签收", "assignee_user_id": U_PM},
    )
    assert sign_task.status_code == 200
    sign_task_id = task_id_by_title(sign_task.json(), "评审签收")

    produce = client.post(
        f"/api/v1/ge/tasks/{task_id}/produces",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gate_item_id},
    )
    assert produce.status_code == 200

    prereq = client.post(
        f"/api/v1/ge/tasks/{sign_task_id}/prerequisites",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gate_item_id},
    )
    assert prereq.status_code == 200, prereq.text


def test_patch_task_title_and_assignee(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    plan = phase_by_name(graph, "方案")
    task_id = plan["tasks"][0]["id"]

    resp = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"title": "更新后的任务", "assignee_user_id": U_PM},
    )
    assert resp.status_code == 200, resp.text
    updated = phase_by_name(resp.json(), "方案")["tasks"][0]
    assert updated["title"] == "更新后的任务"
    assert updated["assignee_user_id"] == U_PM
    assert resp.json()["graph_editable"] is True


def test_reorder_phase_tasks(client):
    project_id = _create_empty_draft(client)
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    phase_id = phase_by_name(graph, "方案")["id"]

    for title in ("任务 A", "任务 B"):
        resp = client.post(
            f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks",
            headers=jwt_headers(U_PM),
            json={"title": title, "assignee_user_id": U_PM},
        )
        assert resp.status_code == 200, resp.text

    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    plan = phase_by_name(graph, "方案")
    task_ids = [task["id"] for task in plan["tasks"]]
    reversed_ids = list(reversed(task_ids))

    resp = client.put(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks/order",
        headers=jwt_headers(U_PM),
        json={"task_ids": reversed_ids},
    )
    assert resp.status_code == 200, resp.text
    next_ids = [task["id"] for task in phase_by_name(resp.json(), "方案")["tasks"]]
    assert next_ids == reversed_ids


def test_produce_link_allowed_when_active(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    assert created["status"] == "active"
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    plan = phase_by_name(graph, "方案")
    task_id = plan["tasks"][0]["id"]
    gate_item_id = plan["gate_items"][0]["id"]
    assert graph["graph_editable"] is True
    resp = client.post(
        f"/api/v1/ge/tasks/{task_id}/produces",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gate_item_id},
    )
    assert resp.status_code == 200


def test_delete_task_requires_no_links(client):
    project_id = _create_empty_draft(client)
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    phase_id = phase_by_name(graph, "方案")["id"]
    task = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/tasks",
        headers=jwt_headers(U_PM),
        json={"title": "临时任务", "assignee_user_id": U_PM},
    )
    assert task.status_code == 200
    plan = phase_by_name(task.json(), "方案")
    task_id = plan["tasks"][0]["id"]

    gate = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "临时门控项", "planned_due": GOLDEN_PLANNED_DUE},
    )
    assert gate.status_code == 200
    gate_item_id = phase_by_name(gate.json(), "方案")["gate_items"][0]["id"]

    client.post(
        f"/api/v1/ge/tasks/{task_id}/produces",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gate_item_id},
    )
    blocked = client.delete(f"/api/v1/ge/tasks/{task_id}", headers=jwt_headers(U_PM))
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "task_has_links"

    client.delete(
        f"/api/v1/ge/tasks/{task_id}/produces/{gate_item_id}",
        headers=jwt_headers(U_PM),
    )
    ok = client.delete(f"/api/v1/ge/tasks/{task_id}", headers=jwt_headers(U_PM))
    assert ok.status_code == 200
    next_graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    assert phase_by_name(next_graph, "方案")["tasks"] == []


def test_patch_and_delete_gate_item(client):
    project_id = _create_empty_draft(client)
    graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_PM)).json()
    phase_id = phase_by_name(graph, "方案")["id"]
    gate = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{phase_id}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "旧名称", "planned_due": GOLDEN_PLANNED_DUE},
    )
    assert gate.status_code == 200
    gate_item_id = phase_by_name(gate.json(), "方案")["gate_items"][0]["id"]

    patched = client.patch(
        f"/api/v1/ge/gate-items/{gate_item_id}",
        headers=jwt_headers(U_PM),
        json={"name": "新名称"},
    )
    assert patched.status_code == 200
    assert phase_by_name(patched.json(), "方案")["gate_items"][0]["name"] == "新名称"

    deleted = client.delete(f"/api/v1/ge/gate-items/{gate_item_id}", headers=jwt_headers(U_PM))
    assert deleted.status_code == 200
    assert phase_by_name(deleted.json(), "方案")["gate_items"] == []
