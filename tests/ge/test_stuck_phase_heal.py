"""Heal active phase whose gate is fully signed but transition was missed on sign."""

from __future__ import annotations

from app.models.ge import GePhase, GeProject
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    phase_by_name,
)


def test_get_graph_repairs_stuck_active_phase_with_open_gate(client):
    """Gate fully signed while phase still active → GET graph completes phase transition."""
    from app.db import session_scope

    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))

    with session_scope() as db:
        project = db.get(GeProject, project_id)
        plan = (
            db.query(GePhase)
            .filter(GePhase.project_id == project_id, GePhase.name == "方案")
            .one()
        )
        dev = (
            db.query(GePhase)
            .filter(GePhase.project_id == project_id, GePhase.name == "开发")
            .one()
        )
        assert project is not None
        assert project.status == "active"
        plan.status = "active"
        dev.status = "pending"
        db.commit()

    with session_scope() as db:
        plan = (
            db.query(GePhase)
            .filter(GePhase.project_id == project_id, GePhase.name == "方案")
            .one()
        )
        dev = (
            db.query(GePhase)
            .filter(GePhase.project_id == project_id, GePhase.name == "开发")
            .one()
        )
        assert plan.status == "active"
        assert dev.status == "pending"

    repaired = get_graph(client, project_id, U_PM)
    plan_phase = phase_by_name(repaired, "方案")
    dev_phase = phase_by_name(repaired, "开发")
    assert plan_phase["status"] == "completed"
    assert dev_phase["status"] == "active"


def _seed_stuck_plan_phase(client, project_id: str) -> None:
    """Sign 方案 GI then force DB stuck state (plan active, dev pending)."""
    from app.db import session_scope

    graph = get_graph(client, project_id, U_PM)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))

    with session_scope() as db:
        project = db.get(GeProject, project_id)
        plan = (
            db.query(GePhase)
            .filter(GePhase.project_id == project_id, GePhase.name == "方案")
            .one()
        )
        dev = (
            db.query(GePhase)
            .filter(GePhase.project_id == project_id, GePhase.name == "开发")
            .one()
        )
        assert project is not None
        assert project.status == "active"
        plan.status = "active"
        dev.status = "pending"
        db.commit()


def test_post_recompute_phases_heals_stuck_phase_for_governor(client):
    """GE-T215: governor POST recompute-phases repairs stuck active phase."""
    created = create_project(client, U_PM)
    project_id = created["id"]
    _seed_stuck_plan_phase(client, project_id)

    resp = client.post(
        f"/api/v1/ge/projects/{project_id}/recompute-phases",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == project_id
    assert body["healed"]["stuck_phases"]

    graph = get_graph(client, project_id, U_PM)
    assert phase_by_name(graph, "方案")["status"] == "completed"
    assert phase_by_name(graph, "开发")["status"] == "active"


def test_post_recompute_phases_forbidden_for_participant(client):
    """GE-T215: non-governor participant receives 403."""
    created = create_project(client, U_PM)
    project_id = created["id"]
    _seed_stuck_plan_phase(client, project_id)

    resp = client.post(
        f"/api/v1/ge/projects/{project_id}/recompute-phases",
        headers=jwt_headers(U_ZHANGSAN),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "not_project_governor"
