"""Default proposal graph on project create."""

from __future__ import annotations

from app.constants import (
    PROPOSAL_GATE_ITEM_NAME,
    PROPOSAL_PHASE_NAME,
    PROPOSAL_RESEARCH_TASK_TITLE,
    PROPOSAL_REVIEW_TASK_TITLE,
    SYSTEM_END_GATE_ITEM_NAME,
    SYSTEM_END_TASK_TITLE,
    SYSTEM_START_GATE_ITEM_NAME,
    SYSTEM_START_TASK_TITLE,
)
from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, create_project, ensure_formal_test_program, get_graph, phase_by_name


def test_create_default_proposal_graph(client):
    program_id = ensure_formal_test_program(client)
    created = create_project(
        client,
        U_PM,
        {
            "name": "默认图项目",
            "pm_user_id": U_PM,
            "program_id": program_id,
            "start_planned_start": "2026-03-01",
            "start_planned_end": "2026-03-07",
            "end_planned_start": "2026-09-24",
            "end_planned_end": "2026-09-30",
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
        bootstrap_startup=False,
        seed_schedule=False,
    )
    graph = get_graph(client, created["id"], U_PM)
    start = phase_by_name(graph, "开始")
    proposal = phase_by_name(graph, PROPOSAL_PHASE_NAME)
    end = phase_by_name(graph, "结束")
    assert start["planned_start"] == "2026-03-01"
    assert start["planned_end"] == "2026-03-07"
    assert proposal["planned_start"] == "2026-03-01"
    assert proposal["planned_end"] == "2026-09-30"
    assert end["planned_start"] == "2026-09-24"
    assert end["planned_end"] == "2026-09-30"

    assert any(gi["name"] == SYSTEM_START_GATE_ITEM_NAME for gi in start["gate_items"])
    assert any(gi["name"] == SYSTEM_END_GATE_ITEM_NAME for gi in end["gate_items"])
    assert any(t["title"] == SYSTEM_START_TASK_TITLE for t in start["tasks"])
    assert any(t["title"] == SYSTEM_END_TASK_TITLE for t in end["tasks"])

    solution = next(gi for gi in proposal["gate_items"] if gi["name"] == PROPOSAL_GATE_ITEM_NAME)
    research = next(t for t in proposal["tasks"] if t["title"] == PROPOSAL_RESEARCH_TASK_TITLE)
    review = next(t for t in proposal["tasks"] if t["title"] == PROPOSAL_REVIEW_TASK_TITLE)
    assert solution["id"] in (review.get("produces") or [])
    start_gi = next(gi for gi in start["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME)
    assert start_gi["id"] in (research.get("prerequisites") or [])
    end_produce = next(t for t in end["tasks"] if t["title"] == SYSTEM_END_TASK_TITLE)
    assert solution["id"] in (end_produce.get("prerequisites") or [])

    assert start_gi["planned_due"] == "2026-03-04"  # mid of 03-01..03-07
    assert solution["planned_due"] == "2026-06-15"  # mid of 03-01..09-30
    end_gi = next(gi for gi in end["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME)
    assert end_gi["planned_due"] == "2026-09-27"  # mid of 09-24..09-30


def test_create_requires_lifecycle_dates(client):
    program_id = ensure_formal_test_program(client)
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(U_PM),
        json={
            "name": "缺日期",
            "pm_user_id": U_PM,
            "program_id": program_id,
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "lifecycle_dates_required"


def test_create_rejects_inverted_lifecycle(client):
    program_id = ensure_formal_test_program(client)
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(U_PM),
        json={
            "name": "倒日期",
            "pm_user_id": U_PM,
            "program_id": program_id,
            "lifecycle_start": "2026-09-01",
            "lifecycle_end": "2026-03-01",
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_lifecycle_window"
