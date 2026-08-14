"""Unit tests for default graph stock migration classification + apply."""

from __future__ import annotations

import uuid

from app.constants import (
    LEGACY_SYSTEM_END_GATE_ITEM_NAME,
    LEGACY_SYSTEM_START_GATE_ITEM_NAME,
    PROPOSAL_GATE_ITEM_NAME,
    PROPOSAL_RESEARCH_TASK_TITLE,
    SYSTEM_END_GATE_ITEM_NAME,
    SYSTEM_START_GATE_ITEM_NAME,
)
from app.db import get_session_factory
from app.models.ge import GeGateItem, GePhase, GeProject, GeTask
from app.services.ge_default_graph_migration import apply_project_plan, classify_project
from tests.ge.conftest import U_PM, create_project, get_graph, phase_by_name


def test_shell_backfill_empty_proposal(client):
    created = create_project(
        client,
        U_PM,
        {
            "name": "空壳",
            "pm_user_id": U_PM,
            "lifecycle_start": "2026-01-01",
            "lifecycle_end": "2026-06-01",
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
        bootstrap_startup=False,
        seed_schedule=False,
    )
    # Simulate legacy GI names on an otherwise default-filled project by renaming back
    factory = get_session_factory()
    with factory() as db:
        project = db.get(GeProject, created["id"])
        assert project is not None
        # Strip proposal content to re-create empty shell middle
        proposal = (
            db.query(GePhase)
            .filter(GePhase.project_id == project.id, GePhase.is_system.is_(False))
            .first()
        )
        assert proposal is not None
        for task in db.query(GeTask).filter(GeTask.phase_id == proposal.id).all():
            db.delete(task)
        for gi in db.query(GeGateItem).filter(GeGateItem.phase_id == proposal.id).all():
            db.delete(gi)
        start = (
            db.query(GePhase)
            .filter(GePhase.project_id == project.id, GePhase.name == "开始")
            .first()
        )
        end = (
            db.query(GePhase)
            .filter(GePhase.project_id == project.id, GePhase.name == "结束")
            .first()
        )
        assert start and end
        start_gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == start.id, GeGateItem.is_system.is_(True))
            .first()
        )
        end_gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == end.id, GeGateItem.is_system.is_(True))
            .first()
        )
        assert start_gi and end_gi
        start_gi.name = LEGACY_SYSTEM_START_GATE_ITEM_NAME
        end_gi.name = LEGACY_SYSTEM_END_GATE_ITEM_NAME
        db.commit()

        plan = classify_project(db, project)
        assert plan.action == "shell_backfill"
        apply_project_plan(db, project, plan)
        db.commit()

    graph = get_graph(client, created["id"], U_PM)
    start = phase_by_name(graph, "开始")
    proposal = phase_by_name(graph, "方案")
    end = phase_by_name(graph, "结束")
    assert any(gi["name"] == SYSTEM_START_GATE_ITEM_NAME for gi in start["gate_items"])
    assert any(gi["name"] == SYSTEM_END_GATE_ITEM_NAME for gi in end["gate_items"])
    assert any(gi["name"] == PROPOSAL_GATE_ITEM_NAME for gi in proposal["gate_items"])
    assert any(t["title"] == PROPOSAL_RESEARCH_TASK_TITLE for t in proposal["tasks"])


def test_rename_only_when_start_signed(client):
    created = create_project(client, U_PM, bootstrap_startup=True, seed_schedule=False)
    factory = get_session_factory()
    with factory() as db:
        project = db.get(GeProject, created["id"])
        assert project is not None
        start = (
            db.query(GePhase)
            .filter(GePhase.project_id == project.id, GePhase.name == "开始")
            .first()
        )
        assert start is not None
        start_gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == start.id, GeGateItem.is_system.is_(True))
            .first()
        )
        assert start_gi is not None
        start_gi.name = LEGACY_SYSTEM_START_GATE_ITEM_NAME
        db.commit()
        plan = classify_project(db, project)
        assert plan.action == "rename_only"
        assert plan.reason == "system_gi_progress"
        apply_project_plan(db, project, plan)
        db.commit()
        db.refresh(start_gi)
        assert start_gi.name == SYSTEM_START_GATE_ITEM_NAME
