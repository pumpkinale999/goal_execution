"""GE-T02–T05 · GE-T09 sign flow tests."""

from __future__ import annotations

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


def _setup_active(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    return created["id"], graph


def test_cross_phase_prerequisite_sign(client):
    project_id, graph = _setup_active(client)
    task_a = task_id_by_title(graph, "编写诊断报告")
    gi_x = gate_item_id_by_name(graph, "诊断报告")

    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report done"),
    )

    sign = client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))
    assert sign.status_code == 200
    assert sign.json()["gate_item"]["status"] == "signed"


def test_or_sign_any_eligible(client):
    project_id, graph = _setup_active(client)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    graph2 = get_graph(client, project_id, U_PM)
    plan_phase = phase_by_name(graph2, "方案")
    assert U_LISI in next(gi["eligible_signers"] for gi in plan_phase["gate_items"] if gi["name"] == "诊断报告")


def test_gate_open_phase_transition(client):
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
    graph_after = get_graph(client, project_id, U_PM)
    plan_phase = phase_by_name(graph_after, "方案")
    dev_phase = phase_by_name(graph_after, "开发")
    assert plan_phase["status"] == "completed"
    assert plan_phase["gate"]["is_open"] is True
    assert dev_phase["status"] == "active"


def test_reject_reopens_produce_task(client):
    project_id, graph = _setup_active(client)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    client.post(f"/api/v1/ge/tasks/{task_a}/done", headers=jwt_headers(U_ZHANGSAN))
    reject = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/reject",
        headers=jwt_headers(U_LISI),
        json={"reject_reason": "needs more detail in the summary field here"},
    )
    assert reject.status_code == 200
    graph_after = get_graph(client, project_id, U_PM)
    plan_phase = phase_by_name(graph_after, "方案")
    task = next(t for t in plan_phase["tasks"] if t["title"] == "编写诊断报告")
    assert task["status"] == "running"


def test_sign_route_task_no_start_done(client):
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

    graph2 = get_graph(client, project_id, U_PM)
    gi_y = gate_item_id_by_name(graph2, "接口规格")
    task_b = task_id_by_title(graph2, "编写接口规格")
    client.post(f"/api/v1/ge/tasks/{task_b}/start", headers=jwt_headers(U_LISI))
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
    task_c = next(t for t in dev_phase["tasks"] if "签收" in t["title"])
    assert task_c["status"] in ("blocked", "ready")
