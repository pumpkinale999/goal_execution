"""GE-T158-B/C/D · v2.28 phase schedule (graph · validate · deviation)."""

from __future__ import annotations

from tests.conftest import jwt_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, create_project, ensure_formal_test_program, get_graph, phase_by_name


def _detail_code(resp) -> str:
    detail = resp.json()["detail"]
    return detail["detail"] if isinstance(detail, dict) else detail


def _set_program_period_db(program_id: str, period_start: str, period_end: str, *, granularity: str = "quarter") -> None:
    from app.db import get_session_factory
    from app.models.ge import GeProgram

    factory = get_session_factory()
    with factory() as db:
        program = db.get(GeProgram, program_id)
        assert program is not None
        program.period_start = period_start
        program.period_end = period_end
        program.period_granularity = granularity
        db.commit()


def _clear_resolved_program_period_db(program_id: str) -> None:
    from app.db import get_session_factory
    from app.models.ge import GeObjective, GeProgram

    factory = get_session_factory()
    with factory() as db:
        program = db.get(GeProgram, program_id)
        assert program is not None
        program.period_start = None
        program.period_end = None
        program.period_granularity = None
        objective = db.get(GeObjective, program.objective_id)
        if objective is not None:
            objective.period_start = None
            objective.period_end = None
            objective.period_granularity = None
        db.commit()


def test_graph_program_period_present(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    assert graph["program_period"]["period_start"] == "2026-01-01"
    assert graph["program_period"]["period_end"] == "2026-12-31"


def test_graph_effective_on_empty_phases(client):
    program_id = ensure_formal_test_program(client)
    _set_program_period_db(program_id, "2026-04-01", "2026-06-30")
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "program_id": program_id}, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    start = graph["phases"][0]
    assert start["is_system"] is True
    assert start["planned_start"] is None
    assert start["effective_planned_start"] == "2026-04-01"
    assert start["effective_planned_end"] == "2026-04-07"
    assert start["planned_window_is_derived"] is True


def test_graph_effective_null_without_program_period(client, ge_db):
    created = create_project(client, U_PM, seed_schedule=False)
    _clear_resolved_program_period_db(created["program_id"])

    graph = get_graph(client, created["id"], U_PM)
    assert graph.get("program_period") is None
    start = graph["phases"][0]
    assert start["effective_planned_start"] is None
    assert start["effective_planned_end"] is None
    assert start["planned_window_is_derived"] is False


def test_graph_program_period_inherited_from_objective(client, ge_db):
    from app.db import get_session_factory
    from app.models.ge import GeObjective, GeProgram

    program_id = ensure_formal_test_program(client)
    _set_program_period_db(program_id, "2026-04-01", "2026-06-30", granularity="quarter")
    factory = get_session_factory()
    with factory() as db:
        program = db.get(GeProgram, program_id)
        assert program is not None
        program.period_start = None
        program.period_end = None
        program.period_granularity = "quarter"
        objective = db.get(GeObjective, program.objective_id)
        assert objective is not None
        objective.period_start = "2026-04-01"
        objective.period_end = "2026-06-30"
        objective.period_granularity = "quarter"
        db.commit()

    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "program_id": program_id}, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    assert graph["program_period"]["period_start"] == "2026-04-01"
    assert graph["program_period"]["period_end"] == "2026-06-30"
    start = graph["phases"][0]
    assert start["effective_planned_start"] == "2026-04-01"
    assert start["planned_window_is_derived"] is True


def test_get_program_resolved_period_inherited(client, ge_db):
    from app.db import get_session_factory
    from app.models.ge import GeObjective, GeProgram

    program_id = ensure_formal_test_program(client)
    factory = get_session_factory()
    with factory() as db:
        program = db.get(GeProgram, program_id)
        assert program is not None
        program.period_start = None
        program.period_end = None
        program.period_granularity = "quarter"
        objective = db.get(GeObjective, program.objective_id)
        assert objective is not None
        objective.period_start = "2026-04-01"
        objective.period_end = "2026-06-30"
        objective.period_granularity = "quarter"
        db.commit()

    resp = client.get(f"/api/v1/ge/programs/{program_id}", headers=jwt_headers(U_PM))
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_start"] is None
    assert body["resolved_period_start"] == "2026-04-01"
    assert body["resolved_period_end"] == "2026-06-30"
    assert body["period_is_inherited"] is True


def test_graph_planned_window_is_derived_flag(client):
    program_id = ensure_formal_test_program(client)
    _set_program_period_db(program_id, "2026-04-01", "2026-06-30")
    body = {
        "name": "排期衍生",
        "pm_user_id": U_PM,
        "program_id": program_id,
        "phases": [
            {"sequence": 1, "name": "方案", "gate_items": [], "tasks": []},
            {"sequence": 2, "name": "开发", "gate_items": [], "tasks": []},
        ],
    }
    created = create_project(client, U_PM, body=body, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    start = graph["phases"][0]
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    client.patch(
        f"/api/v1/ge/phases/{start['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-04-01", "planned_end": "2026-04-07"},
    )
    client.patch(
        f"/api/v1/ge/phases/{plan['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-05-01", "planned_end": "2026-05-31"},
    )
    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-23"},
    )
    assert resp.status_code == 200, resp.text
    graph2 = get_graph(client, created["id"], U_PM)
    dev2 = phase_by_name(graph2, "开发")
    assert dev2["planned_window_is_derived"] is False
    assert dev2["effective_planned_start"] == "2026-06-01"


def test_write_response_includes_effective(client):
    program_id = ensure_formal_test_program(client)
    _set_program_period_db(program_id, "2026-04-01", "2026-06-30")
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "program_id": program_id}, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    start = graph["phases"][0]
    resp = client.patch(
        f"/api/v1/ge/phases/{start['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-04-01", "planned_end": "2026-04-07"},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()["phases"][0]
    assert "effective_planned_start" in updated
    assert updated["effective_planned_start"] == "2026-04-01"
    assert updated["planned_window_is_derived"] is False


def test_adjacent_overlap_same_day(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-15", "planned_end": "2026-06-30"},
    )
    assert resp.status_code == 400
    assert _detail_code(resp) == "phase_schedule_overlap"


def test_adjacent_valid_strict_after(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")
    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-16", "planned_end": "2026-06-30"},
    )
    assert resp.status_code == 200, resp.text


def test_phase_outside_program_period(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")
    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2027-01-01", "planned_end": "2027-01-31"},
    )
    assert resp.status_code == 400
    assert _detail_code(resp) == "phase_schedule_outside_program"


def test_patch_phase_without_program_period(client, ge_db):
    created = create_project(client, U_PM)
    _clear_resolved_program_period_db(created["program_id"])

    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")
    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-30"},
    )
    assert resp.status_code == 400
    assert _detail_code(resp) == "program_period_required"


def test_add_phase_without_program_period(client, ge_db):
    created = create_project(client, U_PM)
    _clear_resolved_program_period_db(created["program_id"])

    resp = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases",
        headers=jwt_headers(U_PM),
        json={"name": "测试阶段", "planned_start": "2026-07-01", "planned_end": "2026-07-31"},
    )
    assert resp.status_code == 400
    assert _detail_code(resp) == "program_period_required"


def test_gate_item_due_uses_effective_window(client):
    program_id = ensure_formal_test_program(client)
    _set_program_period_db(program_id, "2026-04-01", "2026-06-30")
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "program_id": program_id}, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    resp = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{plan['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "有效窗门控项", "planned_due": "2026-04-15"},
    )
    assert resp.status_code == 200, resp.text


def test_patch_phase_revalidates_all_gate_items(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev = phase_by_name(graph, "开发")
    resp = client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-25", "planned_end": "2026-06-30"},
    )
    assert resp.status_code == 400
    assert _detail_code(resp) == "gate_item_schedule_outside_phase"


def test_activate_extends_phase_end(client, monkeypatch):
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    from datetime import date
    from unittest.mock import patch

    from tests.ge.test_deviation import _open_overdue_deviation

    created = create_project(client, U_PM, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    start = graph["phases"][0]
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    end = graph["phases"][-1]
    client.patch(
        f"/api/v1/ge/phases/{start['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-01-01", "planned_end": "2026-01-07"},
    )
    client.patch(
        f"/api/v1/ge/phases/{plan['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-10"},
    )
    client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-20", "planned_end": "2026-06-30"},
    )
    client.patch(
        f"/api/v1/ge/phases/{end['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-12-01", "planned_end": "2026-12-07"},
    )
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        open_body = _open_overdue_deviation(client, get_graph(client, created["id"], U_PM))
    dev_id = open_body["deviation"]["id"]
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "activate",
            "reason": "延期",
            "remediation_plan": "补交",
            "remediation_due": "2026-06-18",
        },
    )
    assert resp.status_code == 200, resp.text
    graph_after = get_graph(client, created["id"], U_PM)
    plan_after = phase_by_name(graph_after, "方案")
    assert plan_after["planned_end"] == "2026-06-18"
    gi = next(gi for phase in graph_after["phases"] for gi in phase["gate_items"] if gi["name"] == "诊断报告")
    assert gi["planned_due"] == "2026-06-18"


def test_deviation_extend_conflicts_next_phase_409(client, monkeypatch):
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    from datetime import date
    from unittest.mock import patch

    from tests.ge.test_deviation import _open_overdue_deviation

    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    dev = phase_by_name(graph, "开发")
    client.patch(
        f"/api/v1/ge/phases/{plan['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-01", "planned_end": "2026-06-15"},
    )
    client.patch(
        f"/api/v1/ge/phases/{dev['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": "2026-06-16", "planned_end": "2026-06-30"},
    )
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        open_body = _open_overdue_deviation(client, get_graph(client, created["id"], U_PM))
    dev_id = open_body["deviation"]["id"]
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "activate",
            "reason": "延期",
            "remediation_plan": "补交",
            "remediation_due": "2026-06-25",
        },
    )
    assert resp.status_code == 409
    assert _detail_code(resp) == "phase_schedule_overlap"
