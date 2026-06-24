"""GE-T26 · audit list API."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import U_LISI, U_PM, U_ZHANGSAN, create_project, gate_item_id_by_name, get_graph, material_submit_payload, task_id_by_title


def test_audit_list_after_submit(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    task_a = task_id_by_title(graph, "编写诊断报告")
    gi_x = gate_item_id_by_name(graph, "诊断报告")

    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )

    resp = client.get(
        "/api/v1/ge/audit-events",
        headers=jwt_headers(U_PM),
        params={"entity_type": "gate_item", "entity_id": gi_x},
    )
    assert resp.status_code == 200
    actions = [row["action"] for row in resp.json()]
    assert "submit" in actions


def test_audit_list_forbidden_for_stranger(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi_x = gate_item_id_by_name(graph, "诊断报告")

    resp = client.get(
        "/api/v1/ge/audit-events",
        headers=jwt_headers("u-stranger"),
        params={"entity_type": "gate_item", "entity_id": gi_x},
    )
    assert resp.status_code == 403
