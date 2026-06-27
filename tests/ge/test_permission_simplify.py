"""GE-T60–T61 · M21 permission simplification."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_PM,
    U_ZHANGSAN,
    create_project,
    get_graph,
    material_submit_payload,
    task_id_by_title,
)


def _gate_item_id(graph, name: str) -> str:
    for phase in graph["phases"]:
        for gi in phase["gate_items"]:
            if gi["name"] == name:
                return gi["id"]
    raise AssertionError(f"gate item {name!r} not found")


def test_pm_can_proxy_submit_and_sign(client):
    """GE-T60"""
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    gi_x = _gate_item_id(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")

    submit = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_PM),
        json=material_submit_payload("PM 代提交"),
    )
    assert submit.status_code == 200, submit.text

    sign = client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_PM))
    assert sign.status_code == 200, sign.text


def test_reviewer_service_token_can_proxy_submit_and_sign(client):
    """GE-T61"""
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    gi_x = _gate_item_id(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")

    submit = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=service_headers("reviewer-1"),
        json=material_submit_payload("评审员代提交"),
    )
    assert submit.status_code == 200, submit.text

    sign = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/sign",
        headers=service_headers("reviewer-1"),
    )
    assert sign.status_code == 200, sign.text


def test_assignee_cannot_graph_edit(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_ZHANGSAN)
    assert graph.get("graph_editable") is not True


def test_stranger_cannot_read_project(client):
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY})
    resp = client.get(f"/api/v1/ge/projects/{created['id']}", headers=jwt_headers("u-stranger"))
    assert resp.status_code == 403
