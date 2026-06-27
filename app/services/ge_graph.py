"""Graph projection and status recompute (§3 · §4.2–§4.6)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.constants import SYSTEM_END_PHASE_NAME, TASK_STATUS_DEVIATED, TASK_STATUS_IDLE
from app.models.ge import (
    GeDeviation,
    GeGate,
    GeGateGateItemInclude,
    GeGateItem,
    GePhase,
    GeProject,
    GeTask,
    GeTaskGateItemPrerequisite,
    GeTaskGateItemProduce,
)
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


def _task_graph_row(db: Session, task: GeTask) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": task.id,
        "title": task.title,
        "assignee_user_id": task.assignee_user_id,
        "phase_id": task.phase_id,
        "produces": _produce_gate_item_ids(db, task.id),
        "prerequisites": _prerequisite_gate_item_ids(db, task.id),
        "is_system": bool(task.is_system),
        "deviation_id": task.deviation_id,
        "is_remediation": task.deviation_id is not None,
    }
    if task.status == TASK_STATUS_DEVIATED:
        row["status"] = TASK_STATUS_DEVIATED
    return row


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


def tasks_linked_to_gate_item(db: Session, gate_item_id: str) -> list[GeTask]:
    """Tasks whose effective_status may change when a GateItem is updated."""
    seen: set[str] = set()
    linked: list[GeTask] = []
    for row in db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.gate_item_id == gate_item_id).all():
        task = db.get(GeTask, row.task_id)
        if task is not None and task.id not in seen:
            seen.add(task.id)
            linked.append(task)
    for row in db.query(GeTaskGateItemPrerequisite).filter(
        GeTaskGateItemPrerequisite.gate_item_id == gate_item_id
    ).all():
        task = db.get(GeTask, row.task_id)
        if task is not None and task.id not in seen:
            seen.add(task.id)
            linked.append(task)
    return linked


def recompute_task_status(db: Session, project_id: str) -> list[GeTask]:
    """Deprecated · M23 — no-op; Task progress is read-time effective_status."""
    _ = (db, project_id)
    return []


def _find_end_system_phase(db: Session, project_id: str) -> GePhase | None:
    return (
        db.query(GePhase)
        .filter(
            GePhase.project_id == project_id,
            GePhase.is_system.is_(True),
            GePhase.name == SYSTEM_END_PHASE_NAME,
        )
        .order_by(GePhase.sequence.desc())
        .first()
    )


def _phase_effectively_done(db: Session, phase: GePhase) -> bool:
    if phase.status == "completed":
        return True
    gate = phase.gate
    return gate is not None and gate_is_open(db, gate, phase)


def maybe_activate_end_phase(db: Session, project_id: str) -> bool:
    """Activate 结束 when all prior phases are done (legacy / backfill safety)."""
    end_phase = _find_end_system_phase(db, project_id)
    if end_phase is None or end_phase.status != "pending":
        return False
    project = load_project_graph(db, project_id)
    if project is None:
        return False
    for phase in sorted(project.phases, key=lambda p: p.sequence):
        if phase.id == end_phase.id:
            continue
        if not _phase_effectively_done(db, phase):
            return False
    end_phase.status = "active"
    end_phase.updated_at = now_iso()
    return True


def reconcile_project_completion(db: Session, project_id: str) -> bool:
    """If 结束 gate is fully signed, mark end phase + project completed.

    Handles stale state where gate items are signed but end phase never went
    through active → apply_phase_transition (common after M20 backfill).
    """
    project = db.get(GeProject, project_id)
    if project is None or project.status != "active":
        return False
    end_phase = _find_end_system_phase(db, project_id)
    if end_phase is None:
        return False
    gate = end_phase.gate
    if gate is None:
        gate = db.query(GeGate).filter(GeGate.phase_id == end_phase.id).first()
    if gate is None or not gate_is_open(db, gate, end_phase):
        return False
    now = now_iso()
    if end_phase.status != "completed":
        end_phase.status = "completed"
        end_phase.updated_at = now
    project.status = "completed"
    project.updated_at = now
    return True


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
    end_phase = _find_end_system_phase(db, project.id)
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
    all_events: list[dict[str, Any]] = []
    while True:
        maybe_activate_end_phase(db, project_id)
        project = load_project_graph(db, project_id)
        if project is None:
            break
        active_phases = [p for p in project.phases if p.status == "active"]
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
        if transitioned:
            continue
        if reconcile_project_completion(db, project_id):
            break
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


def build_project_graph(
    db: Session,
    project: GeProject,
    *,
    actor_user_id: str | None = None,
    is_governor: bool = False,
) -> dict[str, Any]:
    from app.services.ge_deviations import compute_gate_overdue_fields

    deviations_by_gi = {
        d.gate_item_id: d
        for d in db.query(GeDeviation)
        .filter(GeDeviation.project_id == project.id, GeDeviation.status.in_(("open", "active")))
        .all()
    }
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
                        **{
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
                        },
                        **compute_gate_overdue_fields(
                            db,
                            gi,
                            deviation=deviations_by_gi.get(gi.id),
                        ),
                    }
                    for gi in sorted(phase.gate_items, key=lambda g: g.created_at)
                ],
                "tasks": [_task_graph_row(db, task) for task in phase_tasks],
            }
        )
    graph = {
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
    if actor_user_id is not None:
        from app.services.ge_effective_status import attach_effective_status_to_graph

        attach_effective_status_to_graph(
            db,
            graph,
            actor_user_id=actor_user_id,
            is_governor=is_governor,
        )
    return graph


def gate_item_summary(item: GeGateItem, db: Session) -> dict[str, Any]:
    from app.services.ge_deviations import active_deviation_for_gate_item, compute_gate_overdue_fields

    dev = active_deviation_for_gate_item(db, item.id)
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
        **compute_gate_overdue_fields(db, item, deviation=dev),
    }


def write_operation_response(
    db: Session,
    *,
    project: GeProject,
    gate_item: GeGateItem | None,
    affected_tasks: list[GeTask],
    phase: GePhase | None = None,
    gate: GeGate | None = None,
    deviation: GeDeviation | None = None,
    actor_user_id: str | None = None,
    is_governor: bool = False,
) -> dict[str, Any]:
    from app.services.ge_deviations import deviation_summary
    from app.services.ge_effective_status import effective_status_for_task_row

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
                "effective_status": (
                    effective_status_for_task_row(
                        db,
                        task=t,
                        project=project,
                        actor_user_id=actor_user_id,
                        is_governor=is_governor,
                    )
                    if actor_user_id is not None
                    else None
                ),
                "assignee_user_id": t.assignee_user_id,
                "phase_id": t.phase_id,
                "deviation_id": t.deviation_id,
                "is_remediation": t.deviation_id is not None,
                "produces": _produce_gate_item_ids(db, t.id),
                **(
                    {"status": TASK_STATUS_DEVIATED}
                    if t.status == TASK_STATUS_DEVIATED
                    else {}
                ),
            }
            for t in affected_tasks
        ],
        "deviation": deviation_summary(deviation),
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
