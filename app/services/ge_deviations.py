"""Deviation domain logic (M22 · §6)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import (
    GeDeviation,
    GeGateItem,
    GePhase,
    GeProject,
    GeTask,
    GeTaskGateItemProduce,
)
from app.models.org import UserOrgProfile
from app.services.ge_access import require_govern_project
from app.services.ge_graph import (
    now_iso,
    record_audit,
    recompute_task_status,
    task_can_start,
    write_operation_response,
)
from app.services.ge_ws_callback import dispatch_deviation_personal_assistant

SHANGHAI = ZoneInfo("Asia/Shanghai")


def today_shanghai() -> date:
    return datetime.now(SHANGHAI).date()


def _parse_planned_due(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def resolve_report_chain(db: Session, user_id: str) -> list[str]:
    chain: list[str] = []
    seen: set[str] = {user_id}
    current = user_id
    while True:
        profile = db.get(UserOrgProfile, current)
        if profile is None or not profile.manager_user_id:
            break
        manager = profile.manager_user_id
        if manager in seen:
            break
        chain.append(manager)
        seen.add(manager)
        current = manager
    return chain


def notification_recipients(
    db: Session,
    *,
    assignee_user_id: str | None,
    include_report_chain: bool,
) -> list[str]:
    if not assignee_user_id:
        return []
    recipients = [assignee_user_id]
    if include_report_chain:
        recipients.extend(resolve_report_chain(db, assignee_user_id))
    out: list[str] = []
    seen: set[str] = set()
    for uid in recipients:
        if uid and uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out


def active_deviation_for_gate_item(db: Session, gate_item_id: str) -> GeDeviation | None:
    return (
        db.query(GeDeviation)
        .filter(
            GeDeviation.gate_item_id == gate_item_id,
            GeDeviation.status.in_(("open", "active")),
        )
        .first()
    )


def assert_deviation_produce_mutable(db: Session, task_id: str, gate_item_id: str) -> None:
    """Remediation produce while Deviation open/active cannot be edited manually."""
    dev = active_deviation_for_gate_item(db, gate_item_id)
    if dev is not None and dev.remediation_task_id == task_id:
        raise HTTPException(status_code=409, detail={"detail": "deviation_produce_immutable"})


def assert_remediation_produce_link_allowed(
    db: Session,
    task: GeTask,
    gate_item_id: str,
    *,
    existing_produce_task_id: str | None,
) -> None:
    """Block rebinding produce away from remediation or adding second produce during deviation."""
    dev = active_deviation_for_gate_item(db, gate_item_id)
    if dev is not None and existing_produce_task_id == dev.remediation_task_id and task.id != dev.remediation_task_id:
        raise HTTPException(status_code=409, detail={"detail": "deviation_produce_immutable"})
    if task.deviation_id:
        task_dev = db.get(GeDeviation, task.deviation_id)
        if task_dev is not None and task_dev.status in ("open", "active"):
            if existing_produce_task_id != task.id or gate_item_id != task_dev.gate_item_id:
                raise HTTPException(status_code=409, detail={"detail": "deviation_produce_immutable"})


def assert_task_patch_allowed(task: GeTask) -> None:
    if task.status == "deviated":
        raise HTTPException(status_code=409, detail={"detail": "task_deviated_immutable"})


def assert_task_delete_allowed(db: Session, task: GeTask) -> None:
    if task.status == "deviated":
        raise HTTPException(status_code=409, detail={"detail": "task_deviated_immutable"})
    if task.deviation_id is not None:
        raise HTTPException(status_code=409, detail={"detail": "remediation_task_not_deletable"})
    was_remediation = (
        db.query(GeDeviation.id).filter(GeDeviation.remediation_task_id == task.id).first() is not None
    )
    if was_remediation:
        raise HTTPException(status_code=409, detail={"detail": "remediation_task_not_deletable"})


def deviation_for_gate_item(db: Session, gate_item_id: str) -> GeDeviation | None:
    dev = active_deviation_for_gate_item(db, gate_item_id)
    if dev is not None:
        return dev
    return (
        db.query(GeDeviation)
        .filter(GeDeviation.gate_item_id == gate_item_id)
        .order_by(GeDeviation.opened_at.desc())
        .first()
    )


def compute_gate_overdue_fields(
    db: Session,
    item: GeGateItem,
    *,
    deviation: GeDeviation | None = None,
) -> dict[str, Any]:
    if deviation is None:
        deviation = active_deviation_for_gate_item(db, item.id)
    today = today_shanghai()
    planned = _parse_planned_due(item.planned_due)
    is_schedule_overdue = (
        planned is not None and planned < today and item.status not in ("signed",)
    )
    is_remediation_overdue = False
    if deviation is not None and deviation.status in ("open", "active"):
        rem_due = _parse_planned_due(deviation.remediation_due)
        is_remediation_overdue = (
            rem_due is not None and rem_due < today and item.status not in ("signed",)
        )
    has_open_active = deviation is not None and deviation.status in ("open", "active")
    is_overdue = (
        is_schedule_overdue
        and item.status not in ("deviation",)
        and not has_open_active
    )
    return {
        "is_overdue": is_overdue,
        "is_remediation_overdue": is_remediation_overdue,
        "deviation": deviation_summary(deviation) if deviation else None,
    }


def deviation_summary(dev: GeDeviation | None) -> dict[str, Any] | None:
    if dev is None:
        return None
    return {
        "id": dev.id,
        "status": dev.status,
        "kind": dev.kind,
        "revision": dev.revision,
        "remediation_due": dev.remediation_due,
        "remediation_task_id": dev.remediation_task_id,
        "superseded_task_id": dev.superseded_task_id,
    }


def deviation_detail(dev: GeDeviation) -> dict[str, Any]:
    base = deviation_summary(dev) or {}
    return {
        **base,
        "gate_item_id": dev.gate_item_id,
        "project_id": dev.project_id,
        "reason": dev.reason,
        "remediation_plan": dev.remediation_plan,
        "superseded_task_id": dev.superseded_task_id,
        "gate_item_status_at_open": dev.gate_item_status_at_open,
        "superseded_task_status_at_open": dev.superseded_task_status_at_open,
        "opened_by_user_id": dev.opened_by_user_id,
        "opened_at": dev.opened_at,
        "activated_at": dev.activated_at,
        "cancelled_at": dev.cancelled_at,
    }


def _require_governor(project: GeProject, user: AuthUser) -> None:
    require_govern_project(project, user)


def _assert_not_system(item: GeGateItem | None, task: GeTask | None) -> None:
    if item is not None and item.is_system:
        raise HTTPException(status_code=403, detail={"detail": "system_node_not_deviatable"})
    if task is not None and task.is_system:
        raise HTTPException(status_code=403, detail={"detail": "system_node_not_deviatable"})


def assert_deviation_not_open_for_submit(db: Session, gate_item_id: str) -> GeDeviation | None:
    dev = active_deviation_for_gate_item(db, gate_item_id)
    if dev is not None and dev.status == "open":
        raise HTTPException(status_code=409, detail={"detail": "deviation_not_activated"})
    return dev


def open_deviation(
    db: Session,
    gate_item_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    item = db.get(GeGateItem, gate_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    _assert_not_system(item, None)
    phase = db.get(GePhase, item.phase_id)
    if phase is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = db.get(GeProject, phase.project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    _require_governor(project, user)
    if active_deviation_for_gate_item(db, item.id):
        raise HTTPException(status_code=409, detail={"detail": "deviation_already_open"})
    if item.status in ("signed", "deviation"):
        raise HTTPException(status_code=409, detail={"detail": "gate_item_signed"})

    fields = compute_gate_overdue_fields(db, item)
    kind = str(body.get("kind") or "overdue").strip()
    if kind not in ("overdue", "scope"):
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    if kind == "overdue" and not fields["is_overdue"]:
        raise HTTPException(status_code=400, detail={"detail": "deviation_kind_mismatch"})
    if kind == "scope" and fields["is_overdue"]:
        raise HTTPException(status_code=400, detail={"detail": "deviation_kind_mismatch"})

    produce_rows = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.gate_item_id == item.id).all()
    if not produce_rows:
        raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    superseded = db.get(GeTask, produce_rows[0].task_id)
    if superseded is None:
        raise HTTPException(status_code=409, detail={"detail": "gate_item_not_submittable"})
    _assert_not_system(item, superseded)

    now = now_iso()
    dev_id = str(uuid.uuid4())
    remediation_id = str(uuid.uuid4())
    remediation = GeTask(
        id=remediation_id,
        project_id=project.id,
        phase_id=item.phase_id,
        assignee_user_id=superseded.assignee_user_id,
        title=f"补救·{item.name}",
        status="blocked",
        canvas_order=superseded.canvas_order + 1,
        deviation_id=dev_id,
        is_system=False,
        created_at=now,
        updated_at=now,
    )
    dev = GeDeviation(
        id=dev_id,
        gate_item_id=item.id,
        project_id=project.id,
        status="open",
        kind=kind,
        remediation_task_id=remediation_id,
        superseded_task_id=superseded.id,
        gate_item_status_at_open=item.status,
        superseded_task_status_at_open=superseded.status,
        revision=0,
        opened_by_user_id=user.user_id,
        opened_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(dev)
    db.add(remediation)
    db.delete(produce_rows[0])
    db.flush()
    db.add(GeTaskGateItemProduce(task_id=remediation_id, gate_item_id=item.id))
    superseded.status = "deviated"
    superseded.updated_at = now
    item.status = "deviation"
    item.updated_at = now

    if task_can_start(db, remediation, phase):
        remediation.status = "ready"
    affected = recompute_task_status(db, project.id)
    if remediation not in affected:
        affected.append(remediation)
    if superseded not in affected:
        affected.append(superseded)

    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="deviation",
        entity_id=dev.id,
        action="deviation_open",
        payload={"gate_item_id": item.id, "kind": kind},
    )
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="task",
        entity_id=superseded.id,
        action="task_deviated",
        payload={"deviation_id": dev.id},
    )
    db.commit()

    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=phase.gate,
        deviation=dev,
    )


def activate_deviation(
    db: Session,
    deviation_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    dev = db.get(GeDeviation, deviation_id)
    if dev is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = db.get(GeProject, dev.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    _require_governor(project, user)
    if dev.status != "open":
        raise HTTPException(status_code=409, detail={"detail": "deviation_not_open"})

    reason = str(body.get("reason") or "").strip()
    plan = str(body.get("remediation_plan") or "").strip()
    due = str(body.get("remediation_due") or "").strip()
    if not reason or not plan or not due:
        raise HTTPException(status_code=400, detail={"detail": "deviation_activate_incomplete"})

    item = db.get(GeGateItem, dev.gate_item_id)
    remediation = db.get(GeTask, dev.remediation_task_id)
    if item is None or remediation is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    phase = db.get(GePhase, item.phase_id)

    assignee = body.get("assignee_user_id")
    if assignee is not None:
        assignee = str(assignee).strip()
        if assignee:
            remediation.assignee_user_id = assignee

    now = now_iso()
    dev.reason = reason
    dev.remediation_plan = plan
    dev.remediation_due = due[:10]
    dev.status = "active"
    dev.activated_at = now
    dev.updated_at = now
    item.planned_due = dev.remediation_due
    item.updated_at = now
    remediation.updated_at = now

    affected = recompute_task_status(db, project.id)
    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="deviation",
        entity_id=dev.id,
        action="deviation_activate",
        payload={"reason": reason, "remediation_due": dev.remediation_due},
    )
    db.commit()

    recipients = notification_recipients(
        db,
        assignee_user_id=remediation.assignee_user_id,
        include_report_chain=True,
    )
    pa_payload = {
        "deviation_id": dev.id,
        "gate_item_id": item.id,
        "project_id": project.id,
        "project_name": project.name,
        "gate_item_name": item.name,
        "reason": reason,
        "remediation_plan": plan,
        "remediation_due": dev.remediation_due,
        "remediation_task_id": remediation.id,
        "notify_report_chain": True,
    }
    dispatch_deviation_personal_assistant(
        event="ge.deviation.activated",
        recipient_user_ids=recipients,
        payload=pa_payload,
    )

    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=phase.gate if phase else None,
        deviation=dev,
    )


def extend_deviation(
    db: Session,
    deviation_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    dev = db.get(GeDeviation, deviation_id)
    if dev is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = db.get(GeProject, dev.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    _require_governor(project, user)
    if dev.status != "active":
        raise HTTPException(status_code=409, detail={"detail": "deviation_not_active"})

    due = str(body.get("remediation_due") or "").strip()
    extend_reason = str(body.get("extend_reason") or "").strip()
    if not due or not extend_reason:
        raise HTTPException(status_code=400, detail={"detail": "deviation_activate_incomplete"})

    new_revision = dev.revision + 1
    plan_update = body.get("remediation_plan")
    if new_revision >= 3:
        plan_text = str(plan_update or "").strip()
        if not plan_text:
            raise HTTPException(status_code=400, detail={"detail": "deviation_extend_plan_required"})
        dev.remediation_plan = plan_text

    item = db.get(GeGateItem, dev.gate_item_id)
    remediation = db.get(GeTask, dev.remediation_task_id)
    if item is None or remediation is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    phase = db.get(GePhase, item.phase_id)

    now = now_iso()
    dev.remediation_due = due[:10]
    dev.revision = new_revision
    dev.updated_at = now
    item.planned_due = dev.remediation_due
    item.updated_at = now

    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="deviation",
        entity_id=dev.id,
        action="deviation_extend",
        payload={"revision": new_revision, "extend_reason": extend_reason},
    )
    db.commit()

    include_chain = new_revision >= 2
    recipients = notification_recipients(
        db,
        assignee_user_id=remediation.assignee_user_id,
        include_report_chain=include_chain,
    )
    pa_payload = {
        "deviation_id": dev.id,
        "gate_item_id": item.id,
        "project_id": project.id,
        "project_name": project.name,
        "gate_item_name": item.name,
        "revision": new_revision,
        "remediation_due": dev.remediation_due,
        "extend_reason": extend_reason,
        "notify_report_chain": include_chain,
    }
    dispatch_deviation_personal_assistant(
        event="ge.deviation.extended",
        recipient_user_ids=recipients,
        payload=pa_payload,
    )

    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=[remediation],
        phase=phase,
        gate=phase.gate if phase else None,
        deviation=dev,
    )


def cancel_deviation(
    db: Session,
    deviation_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    dev = db.get(GeDeviation, deviation_id)
    if dev is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = db.get(GeProject, dev.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    _require_governor(project, user)
    if dev.status not in ("open", "active"):
        raise HTTPException(status_code=409, detail={"detail": "deviation_not_cancellable"})

    cancel_reason = str(body.get("cancel_reason") or "").strip()
    if not cancel_reason:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})

    item = db.get(GeGateItem, dev.gate_item_id)
    superseded = db.get(GeTask, dev.superseded_task_id)
    remediation = db.get(GeTask, dev.remediation_task_id)
    if item is None or superseded is None or remediation is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    phase = db.get(GePhase, item.phase_id)

    produce_rows = db.query(GeTaskGateItemProduce).filter(GeTaskGateItemProduce.gate_item_id == item.id).all()
    for row in produce_rows:
        db.delete(row)
    db.flush()

    now = now_iso()
    superseded.status = dev.superseded_task_status_at_open
    superseded.updated_at = now
    db.add(GeTaskGateItemProduce(task_id=superseded.id, gate_item_id=item.id))

    remediation.deviation_id = None
    remediation.status = "blocked"
    remediation.updated_at = now

    item.status = dev.gate_item_status_at_open
    item.updated_at = now

    dev.status = "cancelled"
    dev.cancelled_at = now
    dev.updated_at = now

    affected = recompute_task_status(db, project.id)
    for t in (superseded, remediation):
        if t not in affected:
            affected.append(t)

    record_audit(
        db,
        actor_user_id=user.user_id,
        entity_type="deviation",
        entity_id=dev.id,
        action="deviation_cancel",
        payload={
            "cancel_reason": cancel_reason,
            "gate_item_status_at_open": dev.gate_item_status_at_open,
            "superseded_task_status_at_open": dev.superseded_task_status_at_open,
        },
    )
    db.commit()

    return write_operation_response(
        db,
        project=project,
        gate_item=item,
        affected_tasks=affected,
        phase=phase,
        gate=phase.gate if phase else None,
        deviation=dev,
    )


def close_deviation_on_sign(
    db: Session, dev: GeDeviation, item: GeGateItem, signed_by: str
) -> dict[str, Any] | None:
    if dev.status != "active":
        return None
    now = now_iso()
    dev.status = "closed"
    dev.closed_at = now
    dev.updated_at = now
    remediation = db.get(GeTask, dev.remediation_task_id)
    project = db.get(GeProject, dev.project_id)
    if project is None:
        return None

    record_audit(
        db,
        actor_user_id=signed_by,
        entity_type="deviation",
        entity_id=dev.id,
        action="deviation_close",
        payload={"gate_item_id": item.id},
    )

    recipients = notification_recipients(
        db,
        assignee_user_id=remediation.assignee_user_id if remediation else None,
        include_report_chain=True,
    )
    return {
        "event": "ge.deviation.closed",
        "recipient_user_ids": recipients,
        "payload": {
            "deviation_id": dev.id,
            "gate_item_id": item.id,
            "project_id": project.id,
            "project_name": project.name,
            "gate_item_name": item.name,
            "signed_by": signed_by,
            "notify_report_chain": True,
        },
    }


def get_deviation(db: Session, deviation_id: str, user: AuthUser) -> dict[str, Any]:
    dev = db.get(GeDeviation, deviation_id)
    if dev is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    project = db.get(GeProject, dev.project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    from app.services.ge_access import can_read_project

    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_participant"})
    return deviation_detail(dev)


def patch_deviation(
    db: Session,
    deviation_id: str,
    user: AuthUser,
    body: dict[str, Any],
) -> dict[str, Any]:
    action = str(body.get("action") or "").strip()
    if action == "activate":
        return activate_deviation(db, deviation_id, user, body)
    if action == "extend":
        return extend_deviation(db, deviation_id, user, body)
    if action == "cancel":
        return cancel_deviation(db, deviation_id, user, body)
    raise HTTPException(status_code=400, detail={"detail": "invalid_request"})


def build_deviation_actions_for_user(db: Session, user_id: str) -> list[dict[str, Any]]:
    from app.services.ge_access import list_governed_project_ids

    project_ids = list_governed_project_ids(db, user_id)
    if not project_ids:
        return []

    projects = {
        p.id: p
        for p in db.query(GeProject)
        .filter(GeProject.id.in_(project_ids), GeProject.status == "active", GeProject.deleted_at.is_(None))
        .all()
    }
    if not projects:
        return []

    deviations = (
        db.query(GeDeviation, GeGateItem, GePhase)
        .join(GeGateItem, GeGateItem.id == GeDeviation.gate_item_id)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .filter(GeDeviation.project_id.in_(projects.keys()), GeDeviation.status.in_(("open", "active")))
        .all()
    )

    by_gi: dict[str, tuple[str, dict[str, Any]]] = {}
    priority = {"extend": 3, "activate": 2, "open": 1}

    for dev, item, phase in deviations:
        project = projects.get(dev.project_id)
        if project is None:
            continue
        fields = compute_gate_overdue_fields(db, item, deviation=dev)
        if dev.status == "open":
            action = "activate"
        elif dev.status == "active" and fields["is_remediation_overdue"]:
            action = "extend"
        else:
            continue
        entry = {
            "action": action,
            "project_id": project.id,
            "project_name": project.name,
            "gate_item_id": item.id,
            "gate_item_name": item.name,
            "phase_name": phase.name,
            "deviation_id": dev.id,
            "remediation_task_id": dev.remediation_task_id,
        }
        existing = by_gi.get(item.id)
        if existing is None or priority[action] > priority[existing[0]]:
            by_gi[item.id] = (action, entry)

    governed_gi = (
        db.query(GeGateItem, GePhase)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .filter(
            GePhase.project_id.in_(projects.keys()),
            GeGateItem.status.notin_(("signed", "deviation")),
            GeGateItem.is_system.is_(False),
        )
        .all()
    )
    for item, phase in governed_gi:
        if item.id in by_gi:
            continue
        if active_deviation_for_gate_item(db, item.id):
            continue
        fields = compute_gate_overdue_fields(db, item)
        if not fields["is_overdue"]:
            continue
        project = projects.get(phase.project_id)
        if project is None:
            continue
        entry = {
            "action": "open",
            "project_id": project.id,
            "project_name": project.name,
            "gate_item_id": item.id,
            "gate_item_name": item.name,
            "phase_name": phase.name,
            "deviation_id": None,
            "remediation_task_id": None,
        }
        by_gi[item.id] = ("open", entry)

    return [entry for _, entry in by_gi.values()]
