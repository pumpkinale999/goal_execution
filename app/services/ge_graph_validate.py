"""Graph structure validation (§4.2.2)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ge import GeGateGateItemInclude, GeGateItem, GePhase, GeTaskGateItemPrerequisite, GeTaskGateItemProduce
from app.services.ge_graph import load_project_graph
from app.constants import SYSTEM_END_PHASE_NAME
from app.services.ge_system_phases import is_start_phase


def validate_phases_body(phases: list[dict[str, Any]]) -> None:
    if not phases:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    gate_key_to_phase: dict[str, int] = {}
    produce_count: dict[str, int] = {}
    prereq_count: dict[str, int] = {}
    for phase in phases:
        seq = phase.get("sequence")
        for gi in phase.get("gate_items") or []:
            key = gi.get("key")
            if not key:
                raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
            gate_key_to_phase[key] = seq
            produce_count[key] = 0
            prereq_count[key] = 0
            if gi.get("form") != "material":
                raise HTTPException(status_code=400, detail={"detail": "unsupported_gate_item_form"})
        for task in phase.get("tasks") or []:
            if not task.get("assignee_user_id"):
                raise HTTPException(status_code=400, detail={"detail": "invalid_assignee"})
            produces = set(task.get("produces") or [])
            prerequisites = set(task.get("prerequisites") or [])
            if produces & prerequisites:
                raise HTTPException(status_code=400, detail={"detail": "produce_prerequisite_loop"})
            for key in produces:
                if key not in gate_key_to_phase:
                    raise HTTPException(status_code=400, detail={"detail": "unknown_gate_item_key"})
                produce_count[key] = produce_count.get(key, 0) + 1
            for key in prerequisites:
                if key not in gate_key_to_phase:
                    raise HTTPException(status_code=400, detail={"detail": "unknown_gate_item_key"})
                prereq_count[key] = prereq_count.get(key, 0) + 1
                if gate_key_to_phase[key] > seq:
                    raise HTTPException(status_code=400, detail={"detail": "prerequisite_from_future_phase"})
    for key, count in produce_count.items():
        if count != 1:
            raise HTTPException(status_code=400, detail={"detail": "gate_item_unproduced"})
    for key, count in prereq_count.items():
        if count < 1:
            raise HTTPException(status_code=400, detail={"detail": "gate_item_orphan_signer"})


def _produce_gate_item_ids(db: Session, task_id: str) -> list[str]:
    rows = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.task_id == task_id).all()
    return [row.gate_item_id for row in rows]


def _prerequisite_gate_item_ids(db: Session, task_id: str) -> list[str]:
    rows = db.query(GeTaskGateItemPrerequisite).filter(GeTaskGateItemPrerequisite.task_id == task_id).all()
    return [row.gate_item_id for row in rows]


def validate_project_graph_db(db: Session, project_id: str) -> None:
    project = load_project_graph(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})

    gate_item_phase: dict[str, int] = {}
    gate_item_is_system: dict[str, bool] = {}
    produce_count: dict[str, int] = {}
    prereq_count: dict[str, int] = {}
    include_count: dict[str, int] = {}

    for phase in sorted(project.phases, key=lambda p: p.sequence):
        for item in phase.gate_items:
            gate_item_phase[item.id] = phase.sequence
            gate_item_is_system[item.id] = bool(item.is_system)
            produce_count[item.id] = 0
            prereq_count[item.id] = 0
            include_count[item.id] = 0
        gate = phase.gate
        if gate is None:
            continue
        includes = db.query(GeGateGateItemInclude).filter(GeGateGateItemInclude.gate_id == gate.id).count()
        if includes == 0 and not is_start_phase(phase):
            if phase.is_system and phase.name == SYSTEM_END_PHASE_NAME:
                continue
            if len(phase.gate_items) > 0:
                raise HTTPException(status_code=400, detail={"detail": "gate_has_no_items"})

    rows = (
        db.query(GeGateGateItemInclude)
        .join(GeGateItem, GeGateItem.id == GeGateGateItemInclude.gate_item_id)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .filter(GePhase.project_id == project_id)
        .all()
    )
    for row in rows:
        include_count[row.gate_item_id] = include_count.get(row.gate_item_id, 0) + 1

    phase_seq_by_id = {phase.id: phase.sequence for phase in project.phases}
    for task in project.tasks:
        task_seq = phase_seq_by_id.get(task.phase_id)
        if task_seq is None:
            continue
        produces = _produce_gate_item_ids(db, task.id)
        prerequisites = _prerequisite_gate_item_ids(db, task.id)
        if set(produces) & set(prerequisites):
            raise HTTPException(status_code=400, detail={"detail": "produce_prerequisite_loop"})
        for gate_item_id in produces:
            if gate_item_id not in produce_count:
                raise HTTPException(status_code=400, detail={"detail": "unknown_gate_item_key"})
            produce_count[gate_item_id] += 1
        for gate_item_id in prerequisites:
            if gate_item_id not in prereq_count:
                raise HTTPException(status_code=400, detail={"detail": "unknown_gate_item_key"})
            prereq_count[gate_item_id] += 1
            source_seq = gate_item_phase.get(gate_item_id)
            if source_seq is not None and source_seq > task_seq:
                raise HTTPException(status_code=400, detail={"detail": "prerequisite_from_future_phase"})

    for gate_item_id, count in produce_count.items():
        if count != 1:
            raise HTTPException(status_code=400, detail={"detail": "gate_item_unproduced"})
    for gate_item_id, count in prereq_count.items():
        if count < 1:
            if gate_item_is_system.get(gate_item_id):
                continue
            raise HTTPException(status_code=400, detail={"detail": "gate_item_orphan_signer"})
