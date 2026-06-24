"""GE-T28 · entity context for deep links."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, U_STRANGER, create_project, gate_item_id_by_name, get_graph, task_id_by_title


def test_get_task_context(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_id = task_id_by_title(graph, "编写诊断报告")

    resp = client.get(f"/api/v1/ge/tasks/{task_id}", headers=jwt_headers(U_PM))
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == created["id"]
    assert body["task"]["id"] == task_id
    assert body["task"]["title"] == "编写诊断报告"


def test_get_gate_item_context(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi_id = gate_item_id_by_name(graph, "诊断报告")

    resp = client.get(f"/api/v1/ge/gate-items/{gi_id}", headers=jwt_headers(U_PM))
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == created["id"]
    assert body["gate_item"]["id"] == gi_id


def test_get_task_context_forbidden(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_id = task_id_by_title(graph, "编写诊断报告")

    resp = client.get(f"/api/v1/ge/tasks/{task_id}", headers=jwt_headers(U_STRANGER))
    assert resp.status_code == 403


def test_get_task_context_not_found(client):
    resp = client.get("/api/v1/ge/tasks/does-not-exist", headers=jwt_headers(U_PM))
    assert resp.status_code == 404
