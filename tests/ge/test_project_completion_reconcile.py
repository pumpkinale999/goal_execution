"""Project completion when 结束 gate is signed but phase never activated."""

from __future__ import annotations

from app.constants import SYSTEM_END_GATE_ITEM_NAME
from app.models.ge import GePhase, GeProject
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_PM,
    bootstrap_closure_gate,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    phase_by_name,
    task_id_by_title,
)


def test_get_graph_repairs_stale_active_after_end_signed(client):
    """End gate signed while end phase still pending → GET graph completes project."""
    from app.db import session_scope

    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers("u-zhangsan"))
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers("u-zhangsan"),
        json=material_submit_payload("report"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers("u-lisi"))

    graph2 = get_graph(client, project_id, U_PM)
    gi_y = gate_item_id_by_name(graph2, "接口规格")
    task_b = task_id_by_title(graph2, "编写接口规格")
    client.post(f"/api/v1/ge/tasks/{task_b}/start", headers=jwt_headers("u-lisi"))
    client.post(
        f"/api/v1/ge/gate-items/{gi_y}/submit",
        headers=jwt_headers("u-lisi"),
        json=material_submit_payload("spec"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_y}/sign", headers=jwt_headers("u-wangwu"))

    bootstrap_closure_gate(client, project_id, U_PM)

    with session_scope() as db:
        project = db.get(GeProject, project_id)
        end = (
            db.query(GePhase)
            .filter(GePhase.project_id == project_id, GePhase.name == "结束")
            .one()
        )
        assert project is not None
        project.status = "active"
        end.status = "pending"
        db.commit()

    repaired = get_graph(client, project_id, U_PM)
    assert repaired["project"]["status"] == "completed"
    end_phase = phase_by_name(repaired, "结束")
    assert end_phase["status"] == "completed"
    end_gi = next(gi for gi in end_phase["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME)
    assert end_gi["status"] == "signed"
