"""GE-T96–T97 · M23 effective_status (PR1)."""

from __future__ import annotations

from app.db import session_scope
from app.models.ge import GeTask
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_WANGWU,
    U_ZHANGSAN,
    bootstrap_closure_gate,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    phase_by_name,
    task_id_by_title,
)


def _task_by_title(phase: dict, title: str) -> dict:
    for task in phase["tasks"]:
        if task["title"] == title:
            return task
    raise AssertionError(f"task {title} not found")


def _sign_produce_report(client, project_id: str) -> str:
    graph = get_graph(client, project_id, U_PM)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report done"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))
    return task_a


def test_produce_task_effective_status_complete_when_gate_signed(client):
    """GE-T96: signed produce GI → effective_status complete even if DB legacy status."""
    created = create_project(client, U_PM)
    project_id = created["id"]
    task_a = _sign_produce_report(client, project_id)

    with session_scope() as db:
        task_row = db.get(GeTask, task_a)
        assert task_row is not None
        task_row.status = "blocked"
        db.commit()

    graph = get_graph(client, project_id, U_ZHANGSAN)
    plan_phase = phase_by_name(graph, "方案")
    task = _task_by_title(plan_phase, "编写诊断报告")
    assert "status" not in task
    assert task["effective_status"] == "complete"


def test_sign_route_complete_when_project_completed(client):
    """GE-T97: sign-route task complete when prereq signed; project completed OK."""
    created = create_project(client, U_PM)
    project_id = created["id"]
    _sign_produce_report(client, project_id)

    graph2 = get_graph(client, project_id, U_PM)
    gi_y = gate_item_id_by_name(graph2, "接口规格")
    client.post(
        f"/api/v1/ge/gate-items/{gi_y}/submit",
        headers=jwt_headers(U_LISI),
        json=material_submit_payload("spec"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_y}/sign", headers=jwt_headers(U_WANGWU))

    bootstrap_closure_gate(client, project_id, U_PM)

    final = get_graph(client, project_id, U_PM)
    assert final["project"]["status"] == "completed"
    dev_phase = phase_by_name(final, "开发")
    sign_route = _task_by_title(dev_phase, "评审接口规格（签收）")
    assert sign_route["effective_status"] == "complete"


def test_submit_dedup_actionable_tasks_ge_t98(client):
    """GE-T98: after submit assignee → waiting; not in actionable_tasks."""
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_ZHANGSAN)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task = _task_by_title(phase_by_name(graph, "方案"), "编写诊断报告")
    assert task["effective_status"] == "actionable"

    queues_before = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_ZHANGSAN)).json()
    assert len(queues_before["submit"]) >= 1
    assert queues_before["actionable_tasks"] == []

    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    graph_after = get_graph(client, project_id, U_ZHANGSAN)
    task_after = _task_by_title(phase_by_name(graph_after, "方案"), "编写诊断报告")
    assert task_after["effective_status"] == "waiting"

    queues_after = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_ZHANGSAN)).json()
    assert queues_after["submit"] == []
    assert queues_after["actionable_tasks"] == []


def test_start_done_return_410_ge_t99(client):
    """GE-T99: POST start/done → 410 Gone."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_a = task_id_by_title(graph, "编写诊断报告")
    start = client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    assert start.status_code == 410
    done = client.post(f"/api/v1/ge/tasks/{task_a}/done", headers=jwt_headers(U_ZHANGSAN))
    assert done.status_code == 410


def test_deviation_cancel_effective_status_ge_t100(client):
    """GE-T100: cancel deviation rolls back effective_status."""
    from datetime import date
    from unittest.mock import patch

    from tests.ge.conftest import open_deviation

    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    gi = next(
        g for phase in graph["phases"] for g in phase["gate_items"] if g["name"] == "诊断报告"
    )
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        open_body = open_deviation(client, gi["id"], U_PM)
    dev_id = open_body["deviation"]["id"]
    graph_open = get_graph(client, project_id, U_ZHANGSAN)
    orig = next(
        t for phase in graph_open["phases"] for t in phase["tasks"] if t["title"] == "编写诊断报告"
    )
    assert orig["effective_status"] == "deviated"

    client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "cancel", "cancel_reason": "rollback test reason here"},
    )
    graph_cancel = get_graph(client, project_id, U_ZHANGSAN)
    restored = next(
        t for phase in graph_cancel["phases"] for t in phase["tasks"] if t["title"] == "编写诊断报告"
    )
    assert restored["effective_status"] in ("waiting", "actionable")
