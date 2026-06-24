"""Execution notifications read API (§4.4.1 · M18)."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    task_id_by_title,
)


def _setup_active(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    return created["id"], graph


def test_graph_includes_reject_reason(client):
    project_id, graph = _setup_active(client)
    gi_id = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(
        f"/api/v1/ge/gate-items/{gi_id}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    reject = client.post(
        f"/api/v1/ge/gate-items/{gi_id}/reject",
        headers=jwt_headers(U_LISI),
        json={"reject_reason": "needs more detail in the summary field here"},
    )
    assert reject.status_code == 200

    graph_after = get_graph(client, project_id, U_PM)
    gi = next(
        item
        for phase in graph_after["phases"]
        for item in phase["gate_items"]
        if item["id"] == gi_id
    )
    assert gi["status"] == "rejected"
    assert gi["reject_reason"] == "needs more detail in the summary field here"


def test_mark_notification_read(client):
    project_id, graph = _setup_active(client)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))

    unread = client.get(
        "/api/v1/ge/me/execution-notifications?unread_only=true",
        headers=jwt_headers(U_PM),
    )
    assert unread.status_code == 200
    items = unread.json()
    assert len(items) >= 1
    notification_id = items[0]["id"]

    mark = client.post(
        f"/api/v1/ge/me/execution-notifications/{notification_id}/read",
        headers=jwt_headers(U_PM),
    )
    assert mark.status_code == 200
    assert mark.json()["read_at"] is not None

    unread_after = client.get(
        "/api/v1/ge/me/execution-notifications?unread_only=true",
        headers=jwt_headers(U_PM),
    )
    remaining_ids = [item["id"] for item in unread_after.json()]
    assert notification_id not in remaining_ids

    mark_all = client.post(
        "/api/v1/ge/me/execution-notifications/read-all",
        headers=jwt_headers(U_PM),
    )
    assert mark_all.status_code == 200
    assert mark_all.json()["updated"] >= 0
