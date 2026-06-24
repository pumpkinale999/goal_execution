"""Graph projection and status recompute (§3 · §4.2–§4.6)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.constants import SYSTEM_END_PHASE_NAME
from app.models.ge import (
    GeGate,
    GeGateGateItemInclude,
    GeGateItem,
    GePhase,
    GeProject,
    GeTask,
    GeTaskGateItemPrerequisite,
    GeTaskGateItemProduce,
)
from app.constants import SYSTEM_END_PHASE_NAME
from app.services.ge_system_phases import is_start_phase


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_project_graph(db: Session, project_id: str) -> GeProject | None:
    return (
        db.query(GeProject)
        .options(
            joinedload(GeProject.phases).joinedload(GePhase.gate),
            joinedload(GeProject.phases).joinedload(GePhase.gate_items),
            joinedload(GeProject.tasks),
        )
        .filter(GeProject.id == project_id, GeProject.deleted_at.is_(None))
        .first()
    )


def _gate_item_ids_for_gate(db: Session, gate_id: str) -> list[str]:
    rows = db.query(GeGateGateItemInclude).filter(GeGateGateItemInclude.gate_id == gate_id).all()
    return [row.gate_item_id for row in rows]


def _prerequisite_gate_item_ids(db: Session, task_id: str) -> list[str]:
    rows = db.query(GeTaskGateItemPrerequisite).filter(GeTaskGateItemPrerequisite.task_id == task_id).all()
    return [row.gate_item_id for row in rows]


def _produce_gate_item_ids(db: Session, task_id: str) -> list[str]:
    rows = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.task_id == task_id).all()
    return [row.gate_item_id for row in rows]


def eligible_signers(db: Session, gate_item_id: str) -> list[str]:
    rows = (
        db.query(GeTaskGateItemPrerequisite, GeTask)
        .join(GeTask, GeTask.id == GeTaskGateItemPrerequisite.task_id)
        .filter(GeTaskGateItemPrerequisite.gate_item_id == gate_item_id)
        .all()
    )
    signers: list[str] = []
    seen: set[str] = set()
    for _, task in rows:
        if task.assignee_user_id and task.assignee_user_id not in seen:
            seen.add(task.assignee_user_id)
            signers.append(task.assignee_user_id)
    return signers


def gate_is_open(db: Session, gate: GeGate, phase: GePhase | None = None) -> bool:
    if phase is None:
        phase = db.get(GePhase, gate.phase_id)
    if phase is None:
        return False
    items = db.query(GeGateItem).filter(GeGateItem.phase_id == phase.id).all()
    if not items:
        if is_start_phase(phase):
            return True
        if phase.is_system and phase.name == SYSTEM_END_PHASE_NAME:
            return True
        return False
    return all(item.status == "signed" for item in items)


def gate_item_is_signed(item: GeGateItem) -> bool:
    return item.status == "signed"


def task_can_start(db: Session, task: GeTask, phase: GePhase) -> bool:
    if not task.assignee_user_id:
        return False
    if phase.status != "active":
        return False
    for gi_id in _prerequisite_gate_item_ids(db, task.id):
        item = db.get(GeGateItem, gi_id)
        if item is None or not gate_item_is_signed(item):
            return False
    return True


def recompute_task_status(db: Session, project_id: str) -> list[GeTask]:
    changed: list[GeTask] = []
    tasks = db.query(GeTask).filter(GeTask.project_id == project_id).all()
    phases = {p.id: p for p in db.query(GePhase).filter(GePhase.project_id == project_id).all()}
    for task in tasks:
        phase = phases.get(task.phase_id)
        if phase is None:
            continue
        if task.status in ("running", "done"):
            continue
        can_start = task_can_start(db, task, phase)
        new_status = "ready" if can_start else "blocked"
        if task.status != new_status:
            task.status = new_status
            changed.append(task)
    return changed


def apply_phase_transition(db: Session, project: GeProject, opened_phase: GePhase) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    opened_phase.status = "completed"
    opened_phase.updated_at = now_iso()
    events.append(
        {
            "event": "ge.gate.opened",
            "project_id": project.id,
            "phase_id": opened_phase.id,
            "gate_id": opened_phase.gate.id if opened_phase.gate else None,
            "phase_name": opened_phase.name,
            "sequence": opened_phase.sequence,
        }
    )
    end_phase = (
        db.query(GePhase)
        .filter(GePhase.project_id == project.id, GePhase.is_system.is_(True), GePhase.name == SYSTEM_END_PHASE_NAME)
        .order_by(GePhase.sequence.desc())
        .first()
    )
    if end_phase is not None and opened_phase.id == end_phase.id:
        project.status = "completed"
        project.updated_at = now_iso()
        return {"events": events}

    next_phase = (
        db.query(GePhase)
        .filter(GePhase.project_id == project.id, GePhase.sequence == opened_phase.sequence + 1)
        .first()
    )
    if next_phase is not None:
        next_phase.status = "active"
        next_phase.updated_at = now_iso()
        events.append(
            {
                "event": "ge.phase.activated",
                "project_id": project.id,
                "phase_id": next_phase.id,
                "phase_name": next_phase.name,
                "sequence": next_phase.sequence,
            }
        )
    return {"events": events}


def recompute_gate_and_phases(db: Session, project_id: str) -> dict[str, Any]:
    project = load_project_graph(db, project_id)
    if project is None:
        return {"events": []}
    all_events: list[dict[str, Any]] = []
    while True:
        project = load_project_graph(db, project_id)
        if project is None:
            break
        active_phases = [p for p in project.phases if p.status == "active"]
        if not active_phases:
            break
        transitioned = False
        for phase in active_phases:
            gate = phase.gate
            if gate is None:
                continue
            if gate_is_open(db, gate, phase):
                result = apply_phase_transition(db, project, phase)
                all_events.extend(result["events"])
                transitioned = True
                break
        if not transitioned:
            break
    return {"events": all_events}


def project_is_empty(db: Session, project: GeProject) -> bool:
    tasks = (
        db.query(GeTask)
        .filter(GeTask.project_id == project.id, GeTask.is_system.is_(False))
        .count()
    )
    if tasks:
        return False
    items = (
        db.query(GeGateItem)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .filter(GePhase.project_id == project.id, GeGateItem.is_system.is_(False))
        .all()
    )
    if items:
        for item in items:
            if item.status != "draft":
                return False
            if item.submitted_by or item.signed_by or item.rejected_by:
                return False
    for phase in db.query(GePhase).filter(GePhase.project_id == project.id).all():
        if getattr(phase, "is_system", False):
            continue
        if phase.status == "completed":
            return False
    return True


def build_graph_edges(db: Session, project: GeProject) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for task in project.tasks:
        for gi_id in _produce_gate_item_ids(db, task.id):
            edges.append(
                {
                    "id": f"produce:{task.id}:{gi_id}",
                    "kind": "produce",
                    "from": {"type": "task", "id": task.id},
                    "to": {"type": "gate_item", "id": gi_id},
                }
            )
        for gi_id in _prerequisite_gate_item_ids(db, task.id):
            edges.append(
                {
                    "id": f"prerequisite:{gi_id}:{task.id}",
                    "kind": "prerequisite",
                    "from": {"type": "gate_item", "id": gi_id},
                    "to": {"type": "task", "id": task.id},
                }
            )
    return edges


def build_project_graph(db: Session, project: GeProject) -> dict[str, Any]:
    phases_out: list[dict[str, Any]] = []
    for phase in sorted(project.phases, key=lambda p: p.sequence):
        gate = phase.gate
        gate_item_ids = _gate_item_ids_for_gate(db, gate.id) if gate else []
        phase_tasks = sorted(
            [t for t in project.tasks if t.phase_id == phase.id],
            key=lambda t: (t.canvas_order, t.created_at),
        )
        phases_out.append(
            {
                "id": phase.id,
                "sequence": phase.sequence,
                "name": phase.name,
                "status": phase.status,
                "is_system": bool(phase.is_system),
                "planned_start": phase.planned_start,
                "planned_end": phase.planned_end,
                "gate": {
                    "id": gate.id if gate else None,
                    "is_open": gate_is_open(db, gate, phase) if gate else False,
                    "includes": gate_item_ids,
                },
                "gate_items": [
                    {
                        "id": gi.id,
                        "name": gi.name,
                        "form": gi.form,
                        "status": gi.status,
                        "payload": gi.payload_dict,
                        "submitted_by": gi.submitted_by,
                        "signed_by": gi.signed_by,
                        "rejected_by": gi.rejected_by,
                        "submitted_at": gi.submitted_at,
                        "signed_at": gi.signed_at,
                        "rejected_at": gi.rejected_at,
                        "reject_reason": gi.reject_reason,
                        "planned_due": gi.planned_due,
                        "is_system": bool(gi.is_system),
                        "eligible_signers": eligible_signers(db, gi.id),
                    }
                    for gi in sorted(phase.gate_items, key=lambda g: g.created_at)
                ],
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "assignee_user_id": task.assignee_user_id,
                        "phase_id": task.phase_id,
                        "produces": _produce_gate_item_ids(db, task.id),
                        "prerequisites": _prerequisite_gate_item_ids(db, task.id),
                        "is_system": bool(task.is_system),
                    }
                    for task in phase_tasks
                ],
            }
        )
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "pm_user_id": project.pm_user_id,
            "program_id": project.program_id,
            "created_by_user_id": project.created_by_user_id,
            "project_note_id": project.project_note_id,
        },
        "phases": phases_out,
        "edges": build_graph_edges(db, project),
    }


def gate_item_summary(item: GeGateItem, db: Session) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "form": item.form,
        "status": item.status,
        "payload": item.payload_dict,
        "submitted_by": item.submitted_by,
        "signed_by": item.signed_by,
        "rejected_by": item.rejected_by,
        "submitted_at": item.submitted_at,
        "signed_at": item.signed_at,
        "rejected_at": item.rejected_at,
        "reject_reason": item.reject_reason,
        "planned_due": item.planned_due,
        "eligible_signers": eligible_signers(db, item.id),
    }


def write_operation_response(
    db: Session,
    *,
    project: GeProject,
    gate_item: GeGateItem | None,
    affected_tasks: list[GeTask],
    phase: GePhase | None = None,
    gate: GeGate | None = None,
) -> dict[str, Any]:
    phase_obj = phase
    gate_obj = gate
    if gate_item and gate_obj is None:
        phase_obj = db.get(GePhase, gate_item.phase_id)
        gate_obj = phase_obj.gate if phase_obj else None
    if gate_obj and phase_obj is None:
        phase_obj = db.get(GePhase, gate_obj.phase_id)
    return {
        "gate_item": gate_item_summary(gate_item, db) if gate_item else None,
        "affected_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "assignee_user_id": t.assignee_user_id,
                "phase_id": t.phase_id,
            }
            for t in affected_tasks
        ],
        "gate": (
            {
                "id": gate_obj.id,
                "phase_id": gate_obj.phase_id,
                "is_open": gate_is_open(db, gate_obj, phase_obj),
            }
            if gate_obj
            else None
        ),
        "phase": (
            {
                "id": phase_obj.id,
                "sequence": phase_obj.sequence,
                "name": phase_obj.name,
                "status": phase_obj.status,
            }
            if phase_obj
            else None
        ),
        "project": {"id": project.id, "status": project.status},
    }


def record_audit(
    db: Session,
    *,
    actor_user_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    payload: dict[str, Any],
) -> None:
    from app.models.ge import GeAuditEvent

    db.add(
        GeAuditEvent(
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            payload=json.dumps(payload),
            created_at=now_iso(),
        )
    )
