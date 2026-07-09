"""GE-T16 · gate includes auto-sync with phase gate items."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import DEV_PHASE_PLANNED_DUE, U_PM, create_project, get_graph, phase_by_name


def _gate_item_ids(graph: dict, phase_name: str) -> set[str]:
    phase = phase_by_name(graph, phase_name)
    return {gi["id"] for gi in phase["gate_items"]}


def _include_ids(graph: dict, phase_name: str) -> set[str]:
    phase = phase_by_name(graph, phase_name)
    return set(phase["gate"]["includes"] or [])


def test_create_gate_item_syncs_includes(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")

    added = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{dev['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "同步测试项", "planned_due": DEV_PHASE_PLANNED_DUE},
    )
    assert added.status_code == 200
    dev_after = phase_by_name(added.json(), "开发")
    assert _include_ids(added.json(), "开发") == _gate_item_ids(added.json(), "开发")
    assert any(gi["name"] == "同步测试项" for gi in dev_after["gate_items"])


def test_delete_gate_item_syncs_includes(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")

    added = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{dev['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "待删同步项", "planned_due": DEV_PHASE_PLANNED_DUE},
    )
    assert added.status_code == 200
    gi_id = next(gi["id"] for gi in phase_by_name(added.json(), "开发")["gate_items"] if gi["name"] == "待删同步项")

    deleted = client.delete(f"/api/v1/ge/gate-items/{gi_id}", headers=jwt_headers(U_PM))
    assert deleted.status_code == 200
    assert gi_id not in _include_ids(deleted.json(), "开发")
    assert _include_ids(deleted.json(), "开发") == _gate_item_ids(deleted.json(), "开发")


def test_move_gate_item_syncs_includes(client):
    created = create_project(client, U_PM, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")
    test_phase = phase_by_name(graph, "方案")
    gi = next(gi for gi in dev["gate_items"] if gi["name"] == "接口规格")

    moved = client.patch(
        f"/api/v1/ge/gate-items/{gi['id']}",
        headers=jwt_headers(U_PM),
        json={"phase_id": test_phase["id"]},
    )
    assert moved.status_code == 200
    assert gi["id"] not in _include_ids(moved.json(), "开发")
    assert gi["id"] in _include_ids(moved.json(), "方案")
    assert _include_ids(moved.json(), "开发") == _gate_item_ids(moved.json(), "开发")
    assert _include_ids(moved.json(), "方案") == _gate_item_ids(moved.json(), "方案")


def test_manual_include_api_deprecated(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")
    gi = next(gi for gi in dev["gate_items"] if gi["name"] == "接口规格")
    gate_id = dev["gate"]["id"]

    resp = client.post(
        f"/api/v1/ge/gates/{gate_id}/includes",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gi["id"]},
    )
    assert resp.status_code == 410
    detail = resp.json()["detail"]
    assert detail == "gate_includes_automatic" or detail.get("detail") == "gate_includes_automatic"

    delete = client.delete(
        f"/api/v1/ge/gates/{gate_id}/includes/{gi['id']}",
        headers=jwt_headers(U_PM),
    )
    assert delete.status_code == 410


def test_graph_edges_exclude_gate_includes(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    assert not any(edge["kind"] == "gate_includes" for edge in graph["edges"])


def test_cross_phase_produce(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    task_a = next(t for t in plan["tasks"] if t["title"] == "编写诊断报告")

    added = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{dev['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "跨阶段产出项", "planned_due": DEV_PHASE_PLANNED_DUE},
    )
    assert added.status_code == 200
    dev_after = phase_by_name(added.json(), "开发")
    gi_id = next(gi["id"] for gi in dev_after["gate_items"] if gi["name"] == "跨阶段产出项")

    resp = client.post(
        f"/api/v1/ge/tasks/{task_a['id']}/produces",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": gi_id},
    )
    assert resp.status_code == 200
