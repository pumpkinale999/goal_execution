"""GE-T19 · phase PATCH/DELETE."""

from __future__ import annotations

from tests.conftest import jwt_headers
from app.constants import SYSTEM_START_GATE_ITEM_NAME
from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, bootstrap_startup_gate, create_project, get_graph, phase_by_name

EMPTY_SINGLE_PHASE_BODY = {
    "name": "空方案项目",
    "pm_user_id": U_PM,
    "phases": [
        {
            "sequence": 1,
            "name": "方案",
            "gate_items": [],
            "tasks": [],
        },
    ],
}


def test_add_phase_with_planned_window(client):
    created = create_project(client, U_PM)
    project_id = created["id"]

    resp = client.post(
        f"/api/v1/ge/projects/{project_id}/phases",
        headers=jwt_headers(U_PM),
        json={"name": "验收", "planned_start": "2026-04-01", "planned_end": "2026-04-30"},
    )
    assert resp.status_code == 200
    phase = phase_by_name(resp.json(), "验收")
    assert phase["planned_start"] == "2026-04-01"
    assert phase["planned_end"] == "2026-04-30"


def test_add_phase_requires_planned_window(client):
    created = create_project(client, U_PM)
    project_id = created["id"]

    missing_window = client.post(
        f"/api/v1/ge/projects/{project_id}/phases",
        headers=jwt_headers(U_PM),
        json={"name": "无窗口"},
    )
    assert missing_window.status_code == 400
    assert missing_window.json()["detail"] == "phase_planned_window_required"

    missing_name = client.post(
        f"/api/v1/ge/projects/{project_id}/phases",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-04-01", "planned_end": "2026-04-30"},
    )
    assert missing_name.status_code == 400
    assert missing_name.json()["detail"] == "invalid_request"


def test_patch_phase_rename(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")

    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"name": "开发迭代", "planned_start": "2026-06-01", "planned_end": "2026-06-30"},
    )
    assert resp.status_code == 200
    renamed = phase_by_name(resp.json(), "开发迭代")
    assert renamed["id"] == dev["id"]


def test_delete_empty_phase(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)

    added = client.post(
        f"/api/v1/ge/projects/{project_id}/phases",
        headers=jwt_headers(U_PM),
        json={"name": "空阶段", "planned_start": "2026-05-01", "planned_end": "2026-05-31"},
    )
    assert added.status_code == 200
    empty = phase_by_name(added.json(), "空阶段")

    deleted = client.delete(
        f"/api/v1/ge/phases/{empty['id']}",
        headers=jwt_headers(U_PM),
    )
    assert deleted.status_code == 200
    after = deleted.json()
    assert phase_by_name(after, "结束")["sequence"] == max(p["sequence"] for p in after["phases"])
    assert all(p["name"] != "空阶段" for p in after["phases"])


def test_delete_phase_not_empty(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")

    resp = client.delete(
        f"/api/v1/ge/phases/{plan['id']}",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    code = detail["detail"] if isinstance(detail, dict) else detail
    assert code == "phase_not_empty"


def test_delete_empty_active_phase(client):
    """Empty active business phase (e.g. 方案 after Start completes) is deletable; gate goes with it."""
    created = create_project(client, U_PM, body=EMPTY_SINGLE_PHASE_BODY, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    start = phase_by_name(graph, "开始")
    plan = phase_by_name(graph, "方案")
    start_gi = next(gi for gi in start["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME)
    sign_task = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{start['id']}/tasks",
        headers=jwt_headers(U_PM),
        json={"title": "启动签收", "assignee_user_id": U_PM},
    )
    assert sign_task.status_code == 200, sign_task.text
    bootstrap_startup_gate(client, created["id"], U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    assert plan["status"] == "active"
    assert len(plan["gate_items"]) == 0
    assert len(plan["tasks"]) == 0

    resp = client.delete(
        f"/api/v1/ge/phases/{plan['id']}",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 200
    after = resp.json()
    assert all(p["name"] != "方案" for p in after["phases"])
    end = phase_by_name(after, "结束")
    assert end["status"] == "active"


def test_reviewer_service_token_can_delete_empty_phase(client):
    from tests.conftest import service_headers

    created = create_project(client, U_PM, body=EMPTY_SINGLE_PHASE_BODY, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    start = phase_by_name(graph, "开始")
    plan = phase_by_name(graph, "方案")
    client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{start['id']}/tasks",
        headers=jwt_headers(U_PM),
        json={"title": "启动签收", "assignee_user_id": U_PM},
    )
    bootstrap_startup_gate(client, created["id"], U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    assert plan["status"] == "active"

    resp = client.delete(
        f"/api/v1/ge/phases/{plan['id']}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 200
    after = resp.json()
    assert after["graph_deletable"] is True
    assert after["graph_editable"] is True
    assert all(p["name"] != "方案" for p in after["phases"])


def test_resequence_after_gap_from_failed_delete(client):
    """Regression: end phase shrinks without UNIQUE(project_id, sequence) collision."""
    from app.db import get_session_factory
    from app.models.ge import GePhase
    from app.services.ge_system_phases import resequence_with_system_phases

    created = create_project(client, U_PM)
    project_id = created["id"]
    factory = get_session_factory()
    db = factory()
    try:
        phases = db.query(GePhase).filter(GePhase.project_id == project_id).all()
        business = [p for p in phases if not p.is_system]
        assert len(business) >= 2
        end = next(p for p in phases if p.is_system and p.name == "结束")
        # Simulate partial-failure state: business at 2, end still at old max.
        business[1].sequence = 2
        end.sequence = 6
        db.commit()

        resequence_with_system_phases(db, project_id, 0)
        db.commit()
        after = db.query(GePhase).filter(GePhase.project_id == project_id).order_by(GePhase.sequence).all()
        sequences = [p.sequence for p in after]
        assert sequences == list(range(len(after)))
    finally:
        db.close()


def test_delete_two_added_phases(client):
    """Regression: delete two consecutively added empty phases (M12 canvas)."""
    created = create_project(client, U_PM)
    project_id = created["id"]
    g1 = client.post(
        f"/api/v1/ge/projects/{project_id}/phases",
        headers=jwt_headers(U_PM),
        json={"name": "空阶段1", "planned_start": "2026-07-01", "planned_end": "2026-07-15"},
    )
    assert g1.status_code == 200, g1.text
    g2 = client.post(
        f"/api/v1/ge/projects/{project_id}/phases",
        headers=jwt_headers(U_PM),
        json={"name": "空阶段2", "planned_start": "2026-08-01", "planned_end": "2026-08-15"},
    )
    assert g2.status_code == 200, g2.text
    p1 = phase_by_name(g1.json(), "空阶段1")
    p2 = phase_by_name(g2.json(), "空阶段2")

    d1 = client.delete(f"/api/v1/ge/phases/{p1['id']}", headers=jwt_headers(U_PM))
    assert d1.status_code == 200, d1.text
    d2 = client.delete(f"/api/v1/ge/phases/{p2['id']}", headers=jwt_headers(U_PM))
    assert d2.status_code == 200, d2.text


def test_system_phase_name_still_immutable(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    start = graph["phases"][0]
    end = graph["phases"][-1]
    assert start["is_system"] is True
    assert end["is_system"] is True

    patch_start = client.patch(
        f"/api/v1/ge/phases/{start['id']}",
        headers=jwt_headers(U_PM),
        json={"name": "新开始"},
    )
    assert patch_start.status_code == 403
    detail = patch_start.json()["detail"]
    code = detail["detail"] if isinstance(detail, dict) else detail
    assert code == "system_phase_immutable"

    delete_end = client.delete(
        f"/api/v1/ge/phases/{end['id']}",
        headers=jwt_headers(U_PM),
    )
    assert delete_end.status_code == 403
    detail2 = delete_end.json()["detail"]
    code2 = detail2["detail"] if isinstance(detail2, dict) else detail2
    assert code2 == "system_phase_immutable"
