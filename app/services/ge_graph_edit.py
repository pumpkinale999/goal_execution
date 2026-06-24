"""Graph editing: nodes and links (Canvas mouse connect)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser
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
from app.services.ge_access import can_govern_project
from app.services.ge_gate_includes_sync import sync_gate_includes_for_phase
from app.services.ge_graph import build_project_graph, load_project_graph, now_iso, recompute_task_status
from app.services.ge_schedule_validate import (
    parse_plan_date,
    parse_required_plan_date,
    reject_task_schedule_fields,
    require_business_phase_window,
    validate_gate_item_due_in_phase,
    validate_phase_window,
    validate_project_schedule,
)
from app.services.ge_system_phases import assert_not_system_phase, end_phase_for_project, resequence_with_system_phases
from app.services.ge_system_tasks import is_protected_system_end_sign_prerequisite, is_system_end_sign_task


def _assert_not_system_task(task: GeTask) -> None:
    if task.is_system:
        raise HTTPException(status_code=403, detail={"detail": "system_task_immutable"})


def _assert_not_system_gate_item(item: GeGateItem) -> None:
    if item.is_system:
        raise HTTPException(status_code=403, detail={"detail": "system_gate_item_immutable"})


def _activate_successor_phase(db: Session, project_id: str) -> None:
    """After removing the active business phase, activate the next pending one or End."""
    phases = (
        db.query(GePhase)
        .filter(GePhase.project_id == project_id)
        .order_by(GePhase.sequence)
        .all()
    )
    if any(p.status == "active" for p in phases):
        return
    pending_business = [p for p in phases if not p.is_system and p.status == "pending"]
    if pending_business:
        target = min(pending_business, key=lambda p: p.sequence)
    else:
        target = next((p for p in phases if p.is_system and p.name == SYSTEM_END_PHASE_NAME), None)
    if target is not None:
        target.status = "active"
        target.updated_at = now_iso()


def _get_project_or_404(db: Session, project_id: str) -> GeProject:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    return project


def _can_graph_govern(db: Session, project: GeProject, user: AuthUser) -> bool:
    del db
    return can_govern_project(project, user)


def _require_graph_editable(db: Session, project: GeProject, user: AuthUser) -> None:
    if not _can_graph_govern(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "graph_not_editable"})


def graph_deletable_flag(db: Session, project: GeProject, user: AuthUser) -> bool:
    return _can_graph_govern(db, project, user)


def _require_graph_delete(db: Session, project: GeProject, user: AuthUser) -> None:
    _require_graph_editable(db, project, user)


def _get_task_or_404(db: Session, task_id: str) -> GeTask:
    task = db.get(GeTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    return task


def _get_gate_item_or_404(db: Session, gate_item_id: str) -> GeGateItem:
    item = db.get(GeGateItem, gate_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    return item


def _phase_for_gate_item(db: Session, gate_item_id: str) -> GePhase:
    item = _get_gate_item_or_404(db, gate_item_id)
    phase = db.get(GePhase, item.phase_id)
    if phase is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    return phase


def graph_editable_flag(db: Session, project: GeProject, user: AuthUser) -> bool:
    return _can_graph_govern(db, project, user)


def build_editable_project_graph(db: Session, project: GeProject, user: AuthUser) -> dict[str, Any]:
    graph = build_project_graph(db, project)
    graph["graph_editable"] = graph_editable_flag(db, project, user)
    graph["graph_deletable"] = graph_deletable_flag(db, project, user)
    return graph


def add_produce_link(db: Session, task_id: str, gate_item_id: str, user: AuthUser) -> dict[str, Any]:
    task = _get_task_or_404(db, task_id)
    project = _get_project_or_404(db, task.project_id)
    _require_graph_editable(db, project, user)
    item = _get_gate_item_or_404(db, gate_item_id)
    task_phase = db.get(GePhase, task.phase_id)
    item_phase = _phase_for_gate_item(db, gate_item_id)
    if task_phase is None or task_phase.project_id != project.id or item_phase.project_id != project.id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    existing_produce = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.gate_item_id == gate_item_id).first()
    if existing_produce is not None and existing_produce.task_id != task_id:
        raise HTTPException(status_code=409, detail={"detail": "gate_item_already_produced"})
    existing_prereq = (
        db.query(GeTaskGateItemPrerequisite)
        .filter(
            GeTaskGateItemPrerequisite.task_id == task_id,
            GeTaskGateItemPrerequisite.gate_item_id == gate_item_id,
        )
        .first()
    )
    if existing_prereq is not None:
        raise HTTPException(status_code=400, detail={"detail": "produce_prerequisite_loop"})
    if existing_produce is None:
        if item.is_system:
            raise HTTPException(status_code=409, detail={"detail": "gate_item_already_produced"})
        db.add(GeTaskGateItemProduce(task_id=task_id, gate_item_id=gate_item_id))
    project.updated_at = now_iso()
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def remove_produce_link(db: Session, task_id: str, gate_item_id: str, user: AuthUser) -> dict[str, Any]:
    task = _get_task_or_404(db, task_id)
    item = _get_gate_item_or_404(db, gate_item_id)
    _assert_not_system_task(task)
    _assert_not_system_gate_item(item)
    project = _get_project_or_404(db, task.project_id)
    _require_graph_editable(db, project, user)
    row = (
        db.query(GeTaskGateItemProduce)
        .filter(GeTaskGateItemProduce.task_id == task_id, GeTaskGateItemProduce.gate_item_id == gate_item_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    db.delete(row)
    project.updated_at = now_iso()
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def add_prerequisite_link(db: Session, task_id: str, gate_item_id: str, user: AuthUser) -> dict[str, Any]:
    task = _get_task_or_404(db, task_id)
    project = _get_project_or_404(db, task.project_id)
    _require_graph_editable(db, project, user)
    task_phase = db.get(GePhase, task.phase_id)
    item_phase = _phase_for_gate_item(db, gate_item_id)
    if task_phase is None or task_phase.project_id != project.id or item_phase.project_id != project.id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    if item_phase.sequence > task_phase.sequence:
        raise HTTPException(status_code=400, detail={"detail": "prerequisite_from_future_phase"})
    existing_produce = (
        db.query(GeTaskGateItemProduce)
        .filter(GeTaskGateItemProduce.task_id == task_id, GeTaskGateItemProduce.gate_item_id == gate_item_id)
        .first()
    )
    if existing_produce is not None:
        raise HTTPException(status_code=400, detail={"detail": "produce_prerequisite_loop"})
    exists = (
        db.query(GeTaskGateItemPrerequisite)
        .filter(
            GeTaskGateItemPrerequisite.task_id == task_id,
            GeTaskGateItemPrerequisite.gate_item_id == gate_item_id,
        )
        .first()
    )
    if exists is None:
        db.add(GeTaskGateItemPrerequisite(task_id=task_id, gate_item_id=gate_item_id))
    project.updated_at = now_iso()
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def remove_prerequisite_link(db: Session, task_id: str, gate_item_id: str, user: AuthUser) -> dict[str, Any]:
    task = _get_task_or_404(db, task_id)
    project = _get_project_or_404(db, task.project_id)
    _require_graph_editable(db, project, user)
    row = (
        db.query(GeTaskGateItemPrerequisite)
        .filter(
            GeTaskGateItemPrerequisite.task_id == task_id,
            GeTaskGateItemPrerequisite.gate_item_id == gate_item_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if is_protected_system_end_sign_prerequisite(db, task_id=task_id, gate_item_id=gate_item_id):
        raise HTTPException(status_code=403, detail={"detail": "system_sign_route_immutable"})
    db.delete(row)
    project.updated_at = now_iso()
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def add_task(db: Session, project_id: str, phase_id: str, body: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    project = _get_project_or_404(db, project_id)
    _require_graph_editable(db, project, user)
    reject_task_schedule_fields(body)
    phase = db.get(GePhase, phase_id)
    if phase is None or phase.project_id != project_id:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    title = str(body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    assignee = str(body.get("assignee_user_id") or "").strip()
    if not assignee:
        raise HTTPException(status_code=400, detail={"detail": "invalid_assignee"})
    max_order_row = (
        db.query(GeTask.canvas_order)
        .filter(GeTask.phase_id == phase_id)
        .order_by(GeTask.canvas_order.desc())
        .first()
    )
    canvas_order = int(max_order_row[0]) + 1 if max_order_row else 0
    now = now_iso()
    db.add(
        GeTask(
            id=str(uuid.uuid4()),
            project_id=project_id,
            phase_id=phase_id,
            assignee_user_id=assignee,
            title=title,
            status="blocked",
            canvas_order=canvas_order,
            created_at=now,
            updated_at=now,
        )
    )
    project.updated_at = now
    db.commit()
    project_loaded = load_project_graph(db, project_id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def reorder_phase_tasks(
    db: Session,
    project_id: str,
    phase_id: str,
    body: dict[str, Any],
    user: AuthUser,
) -> dict[str, Any]:
    project = _get_project_or_404(db, project_id)
    _require_graph_editable(db, project, user)
    phase = db.get(GePhase, phase_id)
    if phase is None or phase.project_id != project_id:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    raw_ids = body.get("task_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    task_ids = [str(task_id).strip() for task_id in raw_ids if str(task_id).strip()]
    existing = db.query(GeTask).filter(GeTask.phase_id == phase_id).all()
    existing_ids = {task.id for task in existing}
    if len(task_ids) != len(existing_ids) or set(task_ids) != existing_ids:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    system_tasks = sorted([task for task in existing if task.is_system], key=lambda task: task.canvas_order)
    for index, system_task in enumerate(system_tasks):
        if task_ids.index(system_task.id) != index:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    now = now_iso()
    system_order = 0
    non_system_order = len(system_tasks)
    for task_id in task_ids:
        task = db.get(GeTask, task_id)
        if task is None or task.phase_id != phase_id:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        if task.is_system:
            task.canvas_order = system_order
            system_order += 1
        else:
            task.canvas_order = non_system_order
            non_system_order += 1
        task.updated_at = now
    project.updated_at = now
    db.commit()
    project_loaded = load_project_graph(db, project_id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def patch_task(db: Session, task_id: str, body: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    task = _get_task_or_404(db, task_id)
    project = _get_project_or_404(db, task.project_id)
    _require_graph_editable(db, project, user)
    if not body:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    reject_task_schedule_fields(body)
    now = now_iso()
    if task.is_system:
        if "title" in body or "phase_id" in body:
            _assert_not_system_task(task)
    if "title" in body:
        title = str(body.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        task.title = title
    if "assignee_user_id" in body:
        if is_system_end_sign_task(task):
            raise HTTPException(status_code=403, detail={"detail": "system_sign_route_immutable"})
        assignee = str(body.get("assignee_user_id") or "").strip()
        if not assignee:
            raise HTTPException(status_code=400, detail={"detail": "invalid_assignee"})
        task.assignee_user_id = assignee
    if "phase_id" in body:
        new_phase_id = str(body.get("phase_id") or "").strip()
        if not new_phase_id:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        new_phase = db.get(GePhase, new_phase_id)
        if new_phase is None or new_phase.project_id != project.id:
            raise HTTPException(status_code=404, detail={"detail": "not_found"})
        if new_phase_id != task.phase_id:
            task.phase_id = new_phase_id
            max_order_row = (
                db.query(GeTask.canvas_order)
                .filter(GeTask.phase_id == new_phase_id)
                .order_by(GeTask.canvas_order.desc())
                .first()
            )
            task.canvas_order = int(max_order_row[0]) + 1 if max_order_row else 0
    task.updated_at = now
    project.updated_at = now
    if "phase_id" in body:
        recompute_task_status(db, project.id)
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def add_gate_item(db: Session, project_id: str, phase_id: str, body: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    project = _get_project_or_404(db, project_id)
    _require_graph_editable(db, project, user)
    phase = db.get(GePhase, phase_id)
    if phase is None or phase.project_id != project_id:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if phase.is_system:
        raise HTTPException(status_code=403, detail={"detail": "system_gate_item_immutable"})
    gate = db.query(GeGate).filter(GeGate.phase_id == phase_id).first()
    if gate is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    from app.services.ge_gate_item_payload import definition_from_body, parse_form

    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    form = parse_form(body.get("form"))
    definition = definition_from_body(form, body)
    planned_due = parse_required_plan_date(body.get("planned_due"), field="planned_due")
    validate_gate_item_due_in_phase(
        planned_due,
        phase_planned_start=phase.planned_start,
        phase_planned_end=phase.planned_end,
    )
    now = now_iso()
    gi_id = str(uuid.uuid4())
    item = GeGateItem(
        id=gi_id,
        phase_id=phase_id,
        name=name,
        form=form,
        status="draft",
        planned_due=planned_due,
        created_at=now,
        updated_at=now,
    )
    item.payload_dict = definition
    db.add(item)
    db.flush()
    sync_gate_includes_for_phase(db, phase_id)
    project.updated_at = now
    db.commit()
    project_loaded = load_project_graph(db, project_id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def delete_task(db: Session, task_id: str, user: AuthUser) -> dict[str, Any]:
    task = _get_task_or_404(db, task_id)
    _assert_not_system_task(task)
    project = _get_project_or_404(db, task.project_id)
    _require_graph_delete(db, project, user)
    if task.status != "blocked" or task.started_at or task.done_at:
        raise HTTPException(status_code=409, detail={"detail": "task_not_deletable"})
    has_produce = (
        db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.task_id == task_id).first()
        is not None
    )
    has_prereq = (
        db.query(GeTaskGateItemPrerequisite).filter(GeTaskGateItemPrerequisite.task_id == task_id).first()
        is not None
    )
    if has_produce or has_prereq:
        raise HTTPException(status_code=409, detail={"detail": "task_has_links"})
    db.delete(task)
    project.updated_at = now_iso()
    recompute_task_status(db, project.id)
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def patch_gate_item(db: Session, gate_item_id: str, body: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    item = _get_gate_item_or_404(db, gate_item_id)
    phase = _phase_for_gate_item(db, gate_item_id)
    project = _get_project_or_404(db, phase.project_id)
    _require_graph_editable(db, project, user)
    if not body:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    now = now_iso()
    old_phase_id = item.phase_id
    target_phase = phase
    if item.is_system:
        immutable_keys = {"name", "phase_id", "form"}
        if immutable_keys & set(body.keys()):
            _assert_not_system_gate_item(item)
        if any(key in body for key in ("target_value", "operator", "target_state")):
            _assert_not_system_gate_item(item)
    if "name" in body:
        name = str(body.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        item.name = name
    if "phase_id" in body:
        new_phase_id = str(body.get("phase_id") or "").strip()
        if not new_phase_id:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        new_phase = db.get(GePhase, new_phase_id)
        if new_phase is None or new_phase.project_id != project.id:
            raise HTTPException(status_code=404, detail={"detail": "not_found"})
        if new_phase_id != item.phase_id:
            if item.status != "draft" or item.submitted_by or item.signed_by or item.rejected_by:
                raise HTTPException(status_code=409, detail={"detail": "gate_item_not_movable"})
            item.phase_id = new_phase_id
        target_phase = new_phase
    if "planned_due" in body:
        item.planned_due = parse_required_plan_date(body.get("planned_due"), field="planned_due")
    validate_gate_item_due_in_phase(
        item.planned_due,
        phase_planned_start=target_phase.planned_start,
        phase_planned_end=target_phase.planned_end,
    )
    if item.status == "draft" and not item.submitted_by and not item.signed_by and not item.rejected_by:
        from app.services.ge_gate_item_payload import definition_from_body, merge_definition_patch, parse_form

        if "form" in body:
            item.form = parse_form(body.get("form"))
        has_definition_keys = any(
            key in body for key in ("target_value", "operator", "target_state")
        )
        if has_definition_keys or "form" in body:
            if has_definition_keys:
                item.payload_dict = merge_definition_patch(item.payload_dict, item.form, body)
            elif "form" in body:
                item.payload_dict = definition_from_body(item.form, body)
    item.updated_at = now
    project.updated_at = now
    db.flush()
    if item.phase_id != old_phase_id:
        sync_gate_includes_for_phase(db, old_phase_id)
        sync_gate_includes_for_phase(db, item.phase_id)
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def delete_gate_item(db: Session, gate_item_id: str, user: AuthUser) -> dict[str, Any]:
    item = _get_gate_item_or_404(db, gate_item_id)
    _assert_not_system_gate_item(item)
    phase = _phase_for_gate_item(db, gate_item_id)
    project = _get_project_or_404(db, phase.project_id)
    _require_graph_delete(db, project, user)
    if item.status != "draft" or item.submitted_by or item.signed_by or item.rejected_by:
        raise HTTPException(status_code=409, detail={"detail": "gate_item_not_deletable"})
    has_produce = (
        db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.gate_item_id == gate_item_id).first()
        is not None
    )
    has_prereq = (
        db.query(GeTaskGateItemPrerequisite)
        .filter(GeTaskGateItemPrerequisite.gate_item_id == gate_item_id)
        .first()
        is not None
    )
    if has_produce or has_prereq:
        raise HTTPException(status_code=409, detail={"detail": "gate_item_has_links"})
    phase_id = item.phase_id
    db.delete(item)
    db.flush()
    sync_gate_includes_for_phase(db, phase_id)
    project.updated_at = now_iso()
    recompute_task_status(db, project.id)
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def patch_phase(db: Session, phase_id: str, body: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    phase = db.get(GePhase, phase_id)
    if phase is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = _get_project_or_404(db, phase.project_id)
    _require_graph_editable(db, project, user)
    if not body:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    if phase.is_system:
        if "name" in body:
            raise HTTPException(status_code=403, detail={"detail": "system_phase_immutable"})
        extra = set(body.keys()) - {"planned_start", "planned_end"}
        if extra:
            raise HTTPException(status_code=403, detail={"detail": "system_phase_immutable"})
    else:
        if "name" in body:
            name = str(body.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
            phase.name = name
    now = now_iso()
    if "planned_start" in body:
        phase.planned_start = parse_plan_date(body.get("planned_start"), field="planned_start")
    if "planned_end" in body:
        phase.planned_end = parse_plan_date(body.get("planned_end"), field="planned_end")
    if phase.is_system:
        validate_phase_window(phase.planned_start, phase.planned_end)
    else:
        require_business_phase_window(phase.planned_start, phase.planned_end)
    project_phases = db.query(GePhase).filter(GePhase.project_id == project.id).order_by(GePhase.sequence).all()
    validate_project_schedule(project_phases)
    for gi in db.query(GeGateItem).filter(GeGateItem.phase_id == phase_id).all():
        validate_gate_item_due_in_phase(
            gi.planned_due,
            phase_planned_start=phase.planned_start,
            phase_planned_end=phase.planned_end,
        )
    phase.updated_at = now
    project.updated_at = now
    db.commit()
    project_loaded = load_project_graph(db, project.id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def delete_phase(db: Session, phase_id: str, user: AuthUser) -> dict[str, Any]:
    phase = db.get(GePhase, phase_id)
    if phase is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = _get_project_or_404(db, phase.project_id)
    _require_graph_delete(db, project, user)
    assert_not_system_phase(phase)
    has_tasks = db.query(GeTask).filter(GeTask.phase_id == phase_id).first() is not None
    has_gate_items = db.query(GeGateItem).filter(GeGateItem.phase_id == phase_id).first() is not None
    if has_tasks or has_gate_items:
        raise HTTPException(status_code=409, detail={"detail": "phase_not_empty"})
    was_active = phase.status == "active"
    gate = db.query(GeGate).filter(GeGate.phase_id == phase_id).first()
    if gate is not None:
        db.query(GeGateGateItemInclude).filter(GeGateGateItemInclude.gate_id == gate.id).delete()
        db.delete(gate)
    project_id = project.id
    db.delete(phase)
    project.updated_at = now_iso()
    resequence_with_system_phases(db, project_id, 0)
    if was_active:
        _activate_successor_phase(db, project_id)
    db.commit()
    project_loaded = load_project_graph(db, project_id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)


def add_phase(db: Session, project_id: str, body: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    project = _get_project_or_404(db, project_id)
    _require_graph_editable(db, project, user)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    planned_start = parse_plan_date(body.get("planned_start"), field="planned_start")
    planned_end = parse_plan_date(body.get("planned_end"), field="planned_end")
    require_business_phase_window(planned_start, planned_end)
    end_phase = end_phase_for_project(db, project_id)
    if end_phase is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    sequence = end_phase.sequence
    end_phase.sequence = sequence + 1
    end_phase.updated_at = now_iso()
    now = now_iso()
    phase_id = str(uuid.uuid4())
    db.add(
        GePhase(
            id=phase_id,
            project_id=project_id,
            sequence=sequence,
            name=name,
            status="pending",
            is_system=False,
            planned_start=planned_start,
            planned_end=planned_end,
            created_at=now,
            updated_at=now,
        )
    )
    db.add(GeGate(id=str(uuid.uuid4()), phase_id=phase_id))
    project.updated_at = now
    db.flush()
    project_phases = db.query(GePhase).filter(GePhase.project_id == project_id).order_by(GePhase.sequence).all()
    validate_project_schedule(project_phases)
    db.commit()
    project_loaded = load_project_graph(db, project_id)
    assert project_loaded is not None
    return build_editable_project_graph(db, project_loaded, user)
