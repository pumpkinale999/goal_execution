"""GE-T20 · task / gate_item phase_id move."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import GOLDEN_PLANNED_DUE, U_PM, create_project, get_graph, material_submit_payload, phase_by_name, task_id_by_title


def test_move_task_phase(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    task_id = task_id_by_title(graph, "编写诊断报告")
    assert any(t["id"] == task_id for t in plan["tasks"])

    resp = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"phase_id": dev["id"]},
    )
    assert resp.status_code == 200
    after = resp.json()
    dev_after = phase_by_name(after, "开发")
    plan_after = phase_by_name(after, "方案")
    assert any(t["id"] == task_id for t in dev_after["tasks"])
    assert not any(t["id"] == task_id for t in plan_after["tasks"])
    edges = after.get("edges") or []
    assert any(e["kind"] == "produce" and e["from"]["id"] == task_id for e in edges)


def test_move_draft_gate_item_phase(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")

    added = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{plan['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "可移动项", "planned_due": GOLDEN_PLANNED_DUE},
    )
    assert added.status_code == 200
    plan_after_add = phase_by_name(added.json(), "方案")
    gi_id = next(gi["id"] for gi in plan_after_add["gate_items"] if gi["name"] == "可移动项")
    assert gi_id in (plan_after_add["gate"]["includes"] or [])

    moved = client.patch(
        f"/api/v1/ge/gate-items/{gi_id}",
        headers=jwt_headers(U_PM),
        json={"phase_id": dev["id"]},
    )
    assert moved.status_code == 200
    after = moved.json()
    dev_after = phase_by_name(after, "开发")
    plan_after = phase_by_name(after, "方案")
    assert any(gi["id"] == gi_id for gi in dev_after["gate_items"])
    assert gi_id not in (plan_after["gate"].get("includes") or [])
    assert gi_id in (dev_after["gate"].get("includes") or [])


def test_submitted_gate_item_not_movable(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    gi_id = next(gi["id"] for gi in plan["gate_items"] if gi["name"] == "诊断报告")
    task_id = task_id_by_title(graph, "编写诊断报告")

    submit = client.post(
        f"/api/v1/ge/gate-items/{gi_id}/submit",
        headers=jwt_headers("u-zhangsan"),
        json=material_submit_payload("submitted"),
    )
    assert submit.status_code == 200

    resp = client.patch(
        f"/api/v1/ge/gate-items/{gi_id}",
        headers=jwt_headers(U_PM),
        json={"phase_id": dev["id"]},
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    code = detail["detail"] if isinstance(detail, dict) else detail
    assert code == "gate_item_not_movable"


def test_move_task_invalid_phase(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_id = task_id_by_title(graph, "编写诊断报告")

    resp = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_PM),
        json={"phase_id": "00000000-0000-4000-8000-000000000099"},
    )
    assert resp.status_code == 404
