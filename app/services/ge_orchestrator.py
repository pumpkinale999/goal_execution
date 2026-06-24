"""Write operation orchestration (§3)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeGate, GeGateItem, GePhase, GeProject, GeTask, GeTaskGateItemProduce
from app.services.ge_access import can_govern_project, can_read_project, require_govern_project
from app.services.ge_graph import (
    apply_phase_transition,
    eligible_signers,
    gate_is_open,
    load_project_graph,
    now_iso,
    project_is_empty,
    record_audit,
    recompute_gate_and_phases,
    recompute_task_status,
    write_operation_response,
)
from app.services.ge_notifications import upsert_phase_notifications
from app.services.ge_system_tasks import sync_system_end_sign_task_assignee
from app.services.ge_ws_callback import dispatch_ws_events


def _require_active_project(project: GeProject) -> None:
    if project.status != "active":
        raise HTTPException(status_code=409, detail={"detail": "project_not_active"})


def _get_project_or_404(db: Session, project_id: str) -> GeProject:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    return project


def _require_read(db: Session, project: GeProject, user: AuthUser) -> None:
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_participant"})


def soft_delete_project(db: Session, project_id: str, user: AuthUser) -> None:
    project = _get_project_or_404(db, project_id)
    if not can_govern_project(project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_governor"})
    if not project_is_empty(db, project):
        raise HTTPException(status_code=409, detail={"detail": "project_not_empty"})
    project.deleted_at = now_iso()
    project.updated_at = now_iso()
    db.commit()


def _can_act_as_task_assignee(project: GeProject, task: GeTask, user: AuthUser) -> bool:
    if task.assignee_user_id == user.user_id:
        return True
    return can_govern_project(project, user)


def _can_act_as_signer(db: Session, project: GeProject, gate_item_id: str, user: AuthUser) -> bool:
    if user.user_id in eligible_signers(db, gate_item_id):
        return True
    return can_govern_project(project, user)


def patch_project(db: Session, project_id: str, user: AuthUser, body: dict[str, Any]) -> dict[str, Any]:
    project = _get_project_or_404(db, project_id)
    _require_read(db, project, user)
    require_govern_project(project, user)
    if project.status not in ("draft", "active"):
        raise HTTPException(status_code=409, detail={"detail": "project_not_editable"})
    changed = False
    if body.get("name") is not None:
        name = str(body["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail={"detail": "invalid_name"})
        project.name = name
        changed = True
    if body.get("pm_user_id") is not None:
        pm_user_id = str(body["pm_user_id"]).strip()
        if not pm_user_id:
            raise HTTPException(status_code=400, detail={"detail": "invalid_assignee"})
        project.pm_user_id = pm_user_id
        changed = True
    if not changed:
        raise HTTPException(status_code=400, detail={"detail": "no_changes"})
    now = now_iso()
    project.updated_at = now
    sync_system_end_sign_task_assignee(
        db,
        project_id=project.id,
        pm_user_id=project.pm_user_id,
        now=now,
    )
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="project",
        entity_id=project.id,
        action="patch",
        payload={"name": project.name, "pm_user_id": project.pm_user_id},
    )
    db.commit()
    db.refresh(project)
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "pm_user_id": project.pm_user_id,
        "program_id": project.program_id,
        "created_by_user_id": project.created_by_user_id,
        "project_note_id": project.project_note_id,
    }


def _project_summary(project: GeProject) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "pm_user_id": project.pm_user_id,
        "program_id": project.program_id,
        "created_by_user_id": project.created_by_user_id,
        "project_note_id": project.project_note_id,
    }


def bind_project_note_id(
    db: Session,
    project_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    if user.auth_method != "service":
        raise HTTPException(status_code=403, detail={"detail": "service_token_required"})
    project = _get_project_or_404(db, project_id)
    note_id = str(body.get("project_note_id") or "").strip()
    if not note_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_project_note_id"})
    if project.project_note_id:
        raise HTTPException(status_code=409, detail={"detail": "project_note_already_bound"})
    now = now_iso()
    project.project_note_id = note_id
    project.updated_at = now
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="project",
        entity_id=project.id,
        action="bind_note",
        payload={"project_note_id": note_id},
    )
    db.commit()
    db.refresh(project)
    return _project_summary(project)


def submit_gate_item(
    db: Session,
    gate_item_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    item = db.get(GeGateItem, gate_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    phase = db.get(GePhase, item.phase_id)
    gate = phase.gate if phase else None
    project = db.get(GeProject, phase.project_id) if phase else None
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    _require_read(db, project, user)
    _require_active_project(project)
    produce_rows = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.gate_item_id == item.id).all()
    if not produce_rows:
        raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    produce_task = db.get(GeTask, produce_rows[0].task_id)
    if produce_task is None or not _can_act_as_task_assignee(project, produce_task, user):
        raise HTTPException(status_code=403, detail={"detail": "not_assignee"})
    if item.status not in ("draft", "rejected"):
        raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    from app.services.ge_gate_item_payload import validate_submit_payload

    raw_payload = body.get("payload") or {}
    if not isinstance(raw_payload, dict):
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    stored_payload = validate_submit_payload(
        item.form,
        raw_payload,
        item.payload_dict,
        project_note_id=project.project_note_id,
    )
    signers = eligible_signers(db, item.id)
    if not signers:
        raise HTTPException(status_code=400, detail={"detail": "no_eligible_signers"})
    now = now_iso()
    item.payload_dict = stored_payload
    summary = stored_payload.get("summary") or stored_payload.get("actual_value") or item.name
    item.submitted_by = user.user_id
    item.submitted_at = now
    item.status = "pending_sign"
    item.updated_at = now
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="gate_item",
        entity_id=item.id,
        action="submit",
        payload={"summary": summary},
    )
    affected = recompute_task_status(db, project.id)
    gate_events = recompute_gate_and_phases(db, project.id)
    affected = recompute_task_status(db, project.id) + affected
    db.commit()
    ws_payload = {
        "event": "ge.gate_item.submitted",
        "target_user_ids": signers,
        "payload": {
            "gate_item_id": item.id,
            "project_id": project.id,
            "gate_item_name": item.name,
            "submitter_user_id": user.user_id,
        },
    }
    dispatch_ws_events(db, [ws_payload])
    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=gate,
    )


def sign_gate_item(db: Session, gate_item_id: str, user: AuthUser) -> dict[str, Any]:
    item = db.get(GeGateItem, gate_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if item.status != "pending_sign":
        raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    phase = db.get(GePhase, item.phase_id)
    gate = phase.gate if phase else None
    project = db.get(GeProject, phase.project_id) if phase else None
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    _require_read(db, project, user)
    _require_active_project(project)
    if not _can_act_as_signer(db, project, item.id, user):
        raise HTTPException(status_code=403, detail={"detail": "not_eligible_signer"})
    was_open = gate_is_open(db, gate) if gate else False
    now = now_iso()
    item.status = "signed"
    item.signed_by = user.user_id
    item.signed_at = now
    item.updated_at = now
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="gate_item",
        entity_id=item.id,
        action="sign",
        payload={},
    )
    affected = recompute_task_status(db, project.id)
    gate_events = recompute_gate_and_phases(db, project.id)
    affected2 = recompute_task_status(db, project.id)
    affected.extend(affected2)
    db.commit()
    ws_events = []
    for ev in gate_events.get("events", []):
        participants = _participant_ids(db, project)
        ws_events.append(
            {
                "event": ev["event"],
                "target_user_ids": sorted(participants),
                "payload": ev,
            }
        )
        upsert_phase_notifications(db, ev, participants)
    if gate_events.get("events"):
        db.commit()
    dispatch_ws_events(db, ws_events)
    project = load_project_graph(db, project.id) or project
    phase = db.get(GePhase, gate.phase_id) if gate else phase
    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=gate,
    )


def reject_gate_item(
    db: Session,
    gate_item_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    reason = body.get("reject_reason")
    if not reason or not (10 <= len(str(reason)) <= 500):
        raise HTTPException(status_code=400, detail={"detail": "reject_reason_required"})
    item = db.get(GeGateItem, gate_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if item.status != "pending_sign":
        raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    phase = db.get(GePhase, item.phase_id)
    gate = phase.gate if phase else None
    project = db.get(GeProject, phase.project_id) if phase else None
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    _require_read(db, project, user)
    _require_active_project(project)
    if not _can_act_as_signer(db, project, item.id, user):
        raise HTTPException(status_code=403, detail={"detail": "not_eligible_signer"})
    now = now_iso()
    item.status = "rejected"
    item.rejected_by = user.user_id
    item.rejected_at = now
    item.reject_reason = str(reason)
    item.updated_at = now
    produce_rows = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.gate_item_id == item.id).all()
    affected: list[GeTask] = []
    for row in produce_rows:
        task = db.get(GeTask, row.task_id)
        if task and task.status == "done":
            task.status = "running"
            task.done_at = None
            task.updated_at = now
            affected.append(task)
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="gate_item",
        entity_id=item.id,
        action="reject",
        payload={"reject_reason": reason},
    )
    affected.extend(recompute_task_status(db, project.id))
    db.commit()
    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=gate,
    )


def start_task(db: Session, task_id: str, user: AuthUser) -> dict[str, Any]:
    task = db.get(GeTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = _get_project_or_404(db, task.project_id)
    _require_read(db, project, user)
    _require_active_project(project)
    if not _can_act_as_task_assignee(project, task, user):
        raise HTTPException(status_code=403, detail={"detail": "not_assignee"})
    if task.status != "ready":
        raise HTTPException(status_code=409, detail={"detail": "task_not_ready"})
    now = now_iso()
    task.status = "running"
    task.started_at = now
    task.updated_at = now
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="task",
        entity_id=task.id,
        action="start",
        payload={},
    )
    db.commit()
    return write_operation_response(db, project=project, gate_item=None, affected_tasks=[task])


def done_task(db: Session, task_id: str, user: AuthUser) -> dict[str, Any]:
    task = db.get(GeTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = _get_project_or_404(db, task.project_id)
    _require_read(db, project, user)
    _require_active_project(project)
    if not _can_act_as_task_assignee(project, task, user):
        raise HTTPException(status_code=403, detail={"detail": "not_assignee"})
    if task.status != "running":
        raise HTTPException(status_code=409, detail={"detail": "task_not_ready"})
    produce_rows = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.task_id == task.id).all()
    for row in produce_rows:
        item = db.get(GeGateItem, row.gate_item_id)
        if item and item.status not in ("submitted", "pending_sign", "signed"):
            raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    now = now_iso()
    task.status = "done"
    task.done_at = now
    task.updated_at = now
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="task",
        entity_id=task.id,
        action="done",
        payload={},
    )
    db.commit()
    return write_operation_response(db, project=project, gate_item=None, affected_tasks=[task])


def _participant_ids(db: Session, project: GeProject) -> set[str]:
    from app.services.ge_access import project_participant_user_ids

    return project_participant_user_ids(db, project)
