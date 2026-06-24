"""GE-T36–T38 · GateItem form definition and submit payload validation."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_WANGWU,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    phase_by_name,
    task_id_by_title,
)


def _setup_active(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    return created["id"], graph


def test_material_submit_requires_summary(client):
    _, graph = _setup_active(client)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json={"payload": {}},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    if isinstance(detail, dict):
        assert detail["detail"] == "invalid_request"
    else:
        assert detail == "invalid_request"


def test_metric_definition_and_submit(client):
    project_id, graph = _setup_active(client)
    dev_phase = phase_by_name(graph, "开发")
    resp = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{dev_phase['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={
            "name": "性能指标",
            "form": "metric",
            "target_value": 100,
            "operator": ">=",
            "planned_due": "2026-06-18",
        },
    )
    assert resp.status_code == 200, resp.text
    gi_id = next(
        gi["id"]
        for phase in resp.json()["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == "性能指标"
    )
    graph2 = get_graph(client, project_id, U_PM)
    gi = next(
        gi
        for phase in graph2["phases"]
        for gi in phase["gate_items"]
        if gi["id"] == gi_id
    )
    assert gi["form"] == "metric"
    assert gi["payload"]["target_value"] == 100
    assert gi["payload"]["operator"] == ">="

    task_b = task_id_by_title(graph2, "编写接口规格")
    task_c = task_id_by_title(graph2, "评审接口规格（签收）")
    client.post(
        f"/api/v1/ge/tasks/{task_b}/produces",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gi_id},
    )
    client.post(
        f"/api/v1/ge/tasks/{task_c}/prerequisites",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gi_id},
    )
    client.post(f"/api/v1/ge/tasks/{task_b}/start", headers=jwt_headers(U_LISI))
    bad = client.post(
        f"/api/v1/ge/gate-items/{gi_id}/submit",
        headers=jwt_headers(U_LISI),
        json={"payload": {"summary": "wrong field"}},
    )
    assert bad.status_code == 400

    missing_summary = client.post(
        f"/api/v1/ge/gate-items/{gi_id}/submit",
        headers=jwt_headers(U_LISI),
        json={"payload": {"actual_value": 120}},
    )
    assert missing_summary.status_code == 400

    submit = client.post(
        f"/api/v1/ge/gate-items/{gi_id}/submit",
        headers=jwt_headers(U_LISI),
        json={"payload": {"actual_value": 120, "summary": "压测通过，详见项目文档"}},
    )
    assert submit.status_code == 200
    payload = submit.json()["gate_item"]["payload"]
    assert payload["target_value"] == 100
    assert payload["operator"] == ">="
    assert payload["actual_value"] == 120
    assert payload["summary"] == "压测通过，详见项目文档"

    sign = client.post(f"/api/v1/ge/gate-items/{gi_id}/sign", headers=jwt_headers(U_WANGWU))
    assert sign.status_code == 200
    assert sign.json()["gate_item"]["status"] == "signed"


def test_status_definition_and_submit(client):
    project_id, graph = _setup_active(client)
    dev_phase = phase_by_name(graph, "开发")
    resp = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{dev_phase['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={
            "name": "上线状态",
            "form": "status",
            "target_state": "生产环境已部署上线",
            "target_value": True,
            "planned_due": "2026-06-19",
        },
    )
    assert resp.status_code == 200, resp.text
    gi_id = next(
        gi["id"]
        for phase in resp.json()["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == "上线状态"
    )
    task_b = task_id_by_title(graph, "编写接口规格")
    task_c = task_id_by_title(graph, "评审接口规格（签收）")
    client.post(
        f"/api/v1/ge/tasks/{task_b}/produces",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gi_id},
    )
    client.post(
        f"/api/v1/ge/tasks/{task_c}/prerequisites",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gi_id},
    )
    client.post(f"/api/v1/ge/tasks/{task_b}/start", headers=jwt_headers(U_LISI))
    missing_summary = client.post(
        f"/api/v1/ge/gate-items/{gi_id}/submit",
        headers=jwt_headers(U_LISI),
        json={"payload": {"actual_value": True}},
    )
    assert missing_summary.status_code == 400

    submit = client.post(
        f"/api/v1/ge/gate-items/{gi_id}/submit",
        headers=jwt_headers(U_LISI),
        json={"payload": {"actual_value": True, "summary": "release tag v1.0，详见项目文档"}},
    )
    assert submit.status_code == 200
    payload = submit.json()["gate_item"]["payload"]
    assert payload["target_state"] == "生产环境已部署上线"
    assert payload["target_value"] is True
    assert payload["actual_value"] is True
    assert payload["summary"] == "release tag v1.0，详见项目文档"
    assert "evidence" not in payload


def test_patch_gate_item_form_definition_draft(client):
    project_id, graph = _setup_active(client)
    gi_y = gate_item_id_by_name(graph, "接口规格")
    patch = client.patch(
        f"/api/v1/ge/gate-items/{gi_y}",
        headers=jwt_headers(U_PM),
        json={"form": "metric", "target_value": 5, "operator": "=="},
    )
    assert patch.status_code == 200
    gi = next(
        gi
        for phase in patch.json()["phases"]
        for gi in phase["gate_items"]
        if gi["id"] == gi_y
    )
    assert gi["form"] == "metric"
    assert gi["payload"]["target_value"] == 5
    assert gi["payload"]["operator"] == "=="
