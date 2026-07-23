"""Write operation orchestration (§3)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeGate, GeGateItem, GePhase, GeProgram, GeProject, GeTask, GeTaskGateItemProduce
from app.services.ge_access import (
    can_govern_project,
    can_force_delete_project,
    can_read_project,
    require_govern_project,
    require_govern_structure,
)
from app.services.ge_graph import (
    apply_phase_transition,
    eligible_signers,
    load_project_graph,
    now_iso,
    project_is_empty,
    record_audit,
    recompute_gate_and_phases,
    tasks_linked_to_gate_item,
    write_operation_response,
)
from app.services.ge_system_tasks import sync_system_lifecycle_task_assignees
from app.services.ge_subtree_governor import is_subtree_governor
from app.services.ge_sort_order import next_project_sort_order
from app.services.ge_ws_callback import dispatch_deviation_personal_assistant


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
    require_govern_structure(db, project, user)
    if not project_is_empty(db, project) and not can_force_delete_project(db, project, user):
        raise HTTPException(status_code=409, detail={"detail": "project_not_empty"})
    project.deleted_at = now_iso()
    project.updated_at = now_iso()
    db.commit()


def _can_act_as_task_assignee(db: Session, project: GeProject, task: GeTask, user: AuthUser) -> bool:
    if task.assignee_user_id == user.user_id:
        return True
    return can_govern_project(db, project, user)


def _can_act_as_signer(db: Session, project: GeProject, gate_item_id: str, user: AuthUser) -> bool:
    if user.user_id in eligible_signers(db, gate_item_id):
        return True
    return can_govern_project(db, project, user)


def patch_project(db: Session, project_id: str, user: AuthUser, body: dict[str, Any]) -> dict[str, Any]:
    project = _get_project_or_404(db, project_id)
    _require_read(db, project, user)
    require_govern_structure(db, project, user)
    if project.status not in ("draft", "active"):
        raise HTTPException(status_code=409, detail={"detail": "project_not_editable"})
    changed = False
    old_pm_user_id = project.pm_user_id
    pm_changed = False
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
        if pm_user_id != project.pm_user_id:
            pm_changed = True
        project.pm_user_id = pm_user_id
        changed = True
    if body.get("program_id") is not None:
        new_program_id = str(body["program_id"]).strip()
        if not new_program_id:
            raise HTTPException(status_code=400, detail={"detail": "invalid_program_id"})
        if new_program_id != project.program_id:
            _require_program_migration(db, project, user, new_program_id)
            project.program_id = new_program_id
            project.sort_order = next_project_sort_order(db, new_program_id)
            changed = True
    if not changed:
        raise HTTPException(status_code=400, detail={"detail": "no_changes"})
    now = now_iso()
    project.updated_at = now
    if pm_changed:
        from app.services.ge_project_members import replace_pm_on_change

        replace_pm_on_change(
            db,
            project_id=project.id,
            old_pm_user_id=old_pm_user_id,
            new_pm_user_id=project.pm_user_id,
        )
    sync_system_lifecycle_task_assignees(
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
        payload={"name": project.name, "pm_user_id": project.pm_user_id, "program_id": project.program_id},
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


def _can_migrate_program(
    db: Session,
    project: GeProject,
    user: AuthUser,
    *,
    source_program_id: str,
    target_program_id: str,
) -> bool:
    if user.auth_method == "service":
        return True
    if user.auth_method == "jwt" and user.user_id == project.pm_user_id:
        return True
    return is_subtree_governor(db, user_id=user.user_id, program_id=source_program_id) and is_subtree_governor(
        db, user_id=user.user_id, program_id=target_program_id
    )


def _require_program_migration(
    db: Session,
    project: GeProject,
    user: AuthUser,
    target_program_id: str,
) -> None:
    if db.get(GeProgram, target_program_id) is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if not _can_migrate_program(
        db,
        project,
        user,
        source_program_id=project.program_id,
        target_program_id=target_program_id,
    ):
        raise HTTPException(status_code=403, detail={"detail": "not_subtree_governor"})


def migrate_project_program(
    db: Session,
    project_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    project = _get_project_or_404(db, project_id)
    _require_read(db, project, user)
    program_id = body.get("program_id")
    if program_id is None:
        raise HTTPException(status_code=400, detail={"detail": "program_id_required"})
    new_program_id = str(program_id).strip()
    if not new_program_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_program_id"})
    if new_program_id == project.program_id:
        raise HTTPException(status_code=400, detail={"detail": "no_changes"})
    if project.status not in ("draft", "active"):
        raise HTTPException(status_code=409, detail={"detail": "project_not_editable"})
    _require_program_migration(db, project, user, new_program_id)
    old_program_id = project.program_id
    now = now_iso()
    project.program_id = new_program_id
    project.updated_at = now
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="project",
        entity_id=project.id,
        action="migrate_program",
        payload={"from_program_id": old_program_id, "to_program_id": new_program_id},
    )
    db.commit()
    db.refresh(project)
    return _project_summary(project)


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
    if produce_task is None or not _can_act_as_task_assignee(db, project, produce_task, user):
        raise HTTPException(status_code=403, detail={"detail": "not_assignee"})
    from app.services.ge_deviations import active_deviation_for_gate_item, assert_deviation_not_open_for_submit

    dev = assert_deviation_not_open_for_submit(db, item.id)
    if item.status == "deviation":
        if dev is None or dev.status != "active":
            raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    elif item.status not in ("draft", "rejected"):
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
    affected = tasks_linked_to_gate_item(db, item.id)
    recompute_gate_and_phases(db, project.id)
    db.commit()
    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=gate,
        deviation=dev if dev and dev.status in ("open", "active") else None,
        actor_user_id=user.user_id,
        is_governor=can_govern_project(db, project, user),
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
    now = now_iso()
    item.status = "signed"
    item.signed_by = user.user_id
    item.signed_at = now
    item.updated_at = now
    from app.services.ge_deviations import active_deviation_for_gate_item, close_deviation_on_sign

    active_dev = active_deviation_for_gate_item(db, item.id)
    closed_notify = None
    if active_dev is not None:
        closed_notify = close_deviation_on_sign(db, active_dev, item, user.user_id)
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="gate_item",
        entity_id=item.id,
        action="sign",
        payload={},
    )
    affected = tasks_linked_to_gate_item(db, item.id)
    recompute_gate_and_phases(db, project.id)
    db.commit()
    if closed_notify:
        dispatch_deviation_personal_assistant(
            event=closed_notify["event"],
            recipient_user_ids=closed_notify["recipient_user_ids"],
            payload=closed_notify["payload"],
        )
    project_model = db.get(GeProject, project.id) or project
    phase = db.get(GePhase, gate.phase_id) if gate else phase
    closed_dev = active_dev if active_dev and active_dev.status == "closed" else None
    return write_operation_response(
        db,
        project=project_model,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=gate,
        deviation=closed_dev,
        actor_user_id=user.user_id,
        is_governor=can_govern_project(db, project_model, user),
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
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="gate_item",
        entity_id=item.id,
        action="reject",
        payload={"reject_reason": reason},
    )
    affected = tasks_linked_to_gate_item(db, item.id)
    db.commit()
    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=gate,
        actor_user_id=user.user_id,
        is_governor=can_govern_project(db, project, user),
    )


def start_task(db: Session, task_id: str, user: AuthUser) -> dict[str, Any]:
    task = db.get(GeTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = _get_project_or_404(db, task.project_id)
    _require_read(db, project, user)
    _require_active_project(project)
    if not _can_act_as_task_assignee(db, project, task, user):
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
    return write_operation_response(
        db,
        project=project,
        gate_item=None,
        affected_tasks=[task],
        actor_user_id=user.user_id,
        is_governor=can_govern_project(db, project, user),
    )


def done_task(db: Session, task_id: str, user: AuthUser) -> dict[str, Any]:
    task = db.get(GeTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = _get_project_or_404(db, task.project_id)
    _require_read(db, project, user)
    _require_active_project(project)
    if not _can_act_as_task_assignee(db, project, task, user):
        raise HTTPException(status_code=403, detail={"detail": "not_assignee"})
    if task.status != "running":
        raise HTTPException(status_code=409, detail={"detail": "task_not_ready"})
    if task.deviation_id:
        from app.models.ge import GeDeviation

        dev = db.get(GeDeviation, task.deviation_id)
        if dev is not None and dev.status == "open":
            raise HTTPException(status_code=409, detail={"detail": "deviation_not_activated"})
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
    from app.models.ge import GeDeviation

    open_dev = db.get(GeDeviation, task.deviation_id) if task.deviation_id else None
    db.commit()
    return write_operation_response(
        db,
        project=project,
        gate_item=None,
        affected_tasks=[task],
        deviation=open_dev if open_dev and open_dev.status in ("open", "active") else None,
        actor_user_id=user.user_id,
        is_governor=can_govern_project(db, project, user),
    )
