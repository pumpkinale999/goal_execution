"""M12 read APIs: entity context for deep links and audit event listing."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeAuditEvent, GeGateItem, GePhase, GeProject, GeTask
from app.services.ge_access import can_read_project
from app.services.ge_graph import _prerequisite_gate_item_ids, _produce_gate_item_ids, eligible_signers


def _ensure_project_readable(db: Session, project: GeProject | None, user: AuthUser) -> GeProject:
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_participant"})
    return project


def _task_dict(db: Session, task: GeTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "assignee_user_id": task.assignee_user_id,
        "phase_id": task.phase_id,
        "produces": _produce_gate_item_ids(db, task.id),
        "prerequisites": _prerequisite_gate_item_ids(db, task.id),
    }


def _gate_item_dict(db: Session, item: GeGateItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "form": item.form,
        "status": item.status,
        "payload": item.payload_dict,
        "submitted_by": item.submitted_by,
        "signed_by": item.signed_by,
        "rejected_by": item.rejected_by,
        "reject_reason": item.reject_reason,
        "eligible_signers": eligible_signers(db, item.id),
    }


def get_task_context(db: Session, task_id: str, user: AuthUser) -> dict[str, Any]:
    task = db.get(GeTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"detail": "task_not_found"})
    project = _ensure_project_readable(db, db.get(GeProject, task.project_id), user)
    phase = db.get(GePhase, task.phase_id)
    gate_id = phase.gate.id if phase and phase.gate else None
    return {
        "task": _task_dict(db, task),
        "project_id": project.id,
        "phase_id": task.phase_id,
        "gate_id": gate_id,
    }


def get_gate_item_context(db: Session, gate_item_id: str, user: AuthUser) -> dict[str, Any]:
    item = db.get(GeGateItem, gate_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"detail": "gate_item_not_found"})
    phase = db.get(GePhase, item.phase_id)
    if phase is None:
        raise HTTPException(status_code=404, detail={"detail": "gate_item_not_found"})
    project = _ensure_project_readable(db, db.get(GeProject, phase.project_id), user)
    gate_id = phase.gate.id if phase.gate else None
    return {
        "gate_item": _gate_item_dict(db, item),
        "project_id": project.id,
        "phase_id": phase.id,
        "gate_id": gate_id,
    }


def _assert_entity_readable(db: Session, entity_type: str, entity_id: str, user: AuthUser) -> None:
    if entity_type == "task":
        get_task_context(db, entity_id, user)
        return
    if entity_type in ("gate_item", "gate-item"):
        get_gate_item_context(db, entity_id, user)
        return
    raise HTTPException(status_code=400, detail={"detail": "invalid_entity_type"})


def list_audit_events(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    limit: int,
    user: AuthUser,
) -> list[dict[str, Any]]:
    _assert_entity_readable(db, entity_type, entity_id, user)
    normalized_type = "gate_item" if entity_type == "gate-item" else entity_type
    rows = (
        db.query(GeAuditEvent)
        .filter(GeAuditEvent.entity_type == normalized_type, GeAuditEvent.entity_id == entity_id)
        .order_by(GeAuditEvent.created_at.desc(), GeAuditEvent.id.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row.payload or "{}")
        except json.JSONDecodeError:
            payload = {}
        out.append(
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "action": row.action,
                "created_at": row.created_at,
                "payload": payload if isinstance(payload, dict) else {},
            }
        )
    return out
