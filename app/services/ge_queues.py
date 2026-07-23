"""Execution queues (§4.4 · M23 actionable_tasks · M36 ready / governor)."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import (
    GeDeviation,
    GeGateItem,
    GeObjective,
    GePhase,
    GeProgram,
    GeProject,
    GeTask,
    GeTaskGateItemProduce,
)
from app.services.ge_access import can_govern_project
from app.services.ge_deviations import build_deviation_actions_for_user, today_shanghai
from app.services.ge_effective_status import derive_effective_status
from app.services.ge_graph import _produce_gate_item_ids, eligible_signers
from app.services.ge_schedule_derive import build_program_period, derive_phase_effective_window


def _queue_gate_item_ids(submit: list[dict], sign: list[dict]) -> set[str]:
    return {row["gate_item_id"] for row in submit} | {row["gate_item_id"] for row in sign}


def _task_covered_by_queues(task: GeTask, db: Session, queue_gi_ids: set[str]) -> bool:
    produce_ids = _produce_gate_item_ids(db, task.id)
    if produce_ids and any(gi_id in queue_gi_ids for gi_id in produce_ids):
        return True
    from app.models.ge import GeTaskGateItemPrerequisite

    prereq_ids = [
        row.gate_item_id
        for row in db.query(GeTaskGateItemPrerequisite).filter(GeTaskGateItemPrerequisite.task_id == task.id).all()
    ]
    return bool(prereq_ids) and any(gi_id in queue_gi_ids for gi_id in prereq_ids)


def _program_period_for_project(db: Session, project: GeProject) -> dict[str, Any] | None:
    if not project.program_id:
        return None
    program = db.get(GeProgram, project.program_id)
    if program is None:
        return None
    objective = db.get(GeObjective, program.objective_id) if program.objective_id else None
    return build_program_period(program, objective=objective)


def _phases_for_project(db: Session, project_id: str) -> list[GePhase]:
    return (
        db.query(GePhase)
        .filter(GePhase.project_id == project_id)
        .order_by(GePhase.sequence.asc())
        .all()
    )


def _ready_fields(
    phase: GePhase,
    phases: list[GePhase],
    program_period: dict[str, Any] | None,
    today: date,
) -> dict[str, Any]:
    """M36 Ready = effective planned_start calendar day ≤ today (Asia/Shanghai); no start → Ready."""
    eff_start, _, _ = derive_phase_effective_window(
        phases, program_period, target_sequence=phase.sequence
    )
    if not eff_start:
        eff_start = phase.planned_start

    base = {
        "phase_id": phase.id,
        "phase_effective_planned_start": eff_start,
    }
    if not eff_start:
        return {**base, "ready": True, "block_reason": None}
    if date.fromisoformat(eff_start) <= today:
        return {**base, "ready": True, "block_reason": None}
    return {**base, "ready": False, "block_reason": "not_yet_started"}


def _submit_eligible(db: Session, item: GeGateItem) -> bool:
    if item.status in ("draft", "rejected"):
        return True
    if item.status == "deviation":
        return (
            db.query(GeDeviation)
            .filter(GeDeviation.gate_item_id == item.id, GeDeviation.status == "active")
            .first()
            is not None
        )
    return False


def _gate_row(
    *,
    item: GeGateItem,
    project: GeProject,
    phase: GePhase,
    ready_meta: dict[str, Any],
    as_governor: bool,
    submitted_by: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "gate_item_id": item.id,
        "gate_item_name": item.name,
        "project_id": project.id,
        "project_name": project.name,
        "phase_name": phase.name,
        **ready_meta,
        "as_governor": as_governor,
    }
    if submitted_by is not None:
        row["submitted_by_user_id"] = submitted_by
    return row


def build_queues(db: Session, user_id: str) -> dict:
    submit: list[dict] = []
    sign: list[dict] = []
    actionable_tasks: list[dict] = []
    today = today_shanghai()
    auth = AuthUser(user_id=user_id, auth_method="jwt")

    active_projects = db.query(GeProject).filter(GeProject.status == "active", GeProject.deleted_at.is_(None)).all()
    project_map = {p.id: p for p in active_projects}

    # Cache: project_id → (phases, program_period, is_governor)
    project_ctx: dict[str, tuple[list[GePhase], dict[str, Any] | None, bool]] = {}

    def ctx_for(project: GeProject) -> tuple[list[GePhase], dict[str, Any] | None, bool]:
        cached = project_ctx.get(project.id)
        if cached is not None:
            return cached
        phases = _phases_for_project(db, project.id)
        period = _program_period_for_project(db, project)
        is_gov = can_govern_project(db, project, auth)
        entry = (phases, period, is_gov)
        project_ctx[project.id] = entry
        return entry

    produce_rows = (
        db.query(GeTaskGateItemProduce, GeTask, GeGateItem, GePhase)
        .join(GeTask, GeTask.id == GeTaskGateItemProduce.task_id)
        .join(GeGateItem, GeGateItem.id == GeTaskGateItemProduce.gate_item_id)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .all()
    )
    submit_seen: set[str] = set()
    for _, task, item, phase in produce_rows:
        project = project_map.get(task.project_id)
        if project is None:
            continue
        if not _submit_eligible(db, item):
            continue
        phases, period, is_gov = ctx_for(project)
        is_assignee = task.assignee_user_id == user_id
        if not is_assignee and not is_gov:
            continue
        if item.id in submit_seen:
            continue
        submit_seen.add(item.id)
        ready_meta = _ready_fields(phase, phases, period, today)
        submit.append(
            _gate_row(
                item=item,
                project=project,
                phase=phase,
                ready_meta=ready_meta,
                as_governor=bool(is_gov and not is_assignee),
            )
        )

    pending_items = (
        db.query(GeGateItem, GePhase, GeProject)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .join(GeProject, GeProject.id == GePhase.project_id)
        .filter(GeGateItem.status == "pending_sign", GeProject.status == "active", GeProject.deleted_at.is_(None))
        .all()
    )
    for item, phase, project in pending_items:
        phases, period, is_gov = ctx_for(project)
        signers = eligible_signers(db, item.id)
        is_signer = user_id in signers
        if not is_signer and not is_gov:
            continue
        ready_meta = _ready_fields(phase, phases, period, today)
        sign.append(
            _gate_row(
                item=item,
                project=project,
                phase=phase,
                ready_meta=ready_meta,
                as_governor=bool(is_gov and not is_signer),
                submitted_by=item.submitted_by,
            )
        )

    deviation_actions = build_deviation_actions_for_user(db, user_id)
    for entry in deviation_actions:
        project = project_map.get(entry["project_id"])
        if project is None:
            continue
        phases, period, _ = ctx_for(project)
        phase = next((p for p in phases if p.name == entry.get("phase_name")), None)
        if phase is None:
            gi = db.get(GeGateItem, entry["gate_item_id"])
            phase = db.get(GePhase, gi.phase_id) if gi else None
        if phase is None:
            entry["ready"] = True
            entry["block_reason"] = None
            entry["phase_id"] = None
            entry["phase_effective_planned_start"] = None
            entry["as_governor"] = True
            continue
        ready_meta = _ready_fields(phase, phases, period, today)
        entry.update(ready_meta)
        entry["as_governor"] = True

    queue_gi_ids = _queue_gate_item_ids(submit, sign)
    candidate_tasks = (
        db.query(GeTask, GePhase, GeProject)
        .join(GePhase, GePhase.id == GeTask.phase_id)
        .join(GeProject, GeProject.id == GeTask.project_id)
        .filter(
            GeTask.assignee_user_id == user_id,
            GeProject.status == "active",
            GeProject.deleted_at.is_(None),
        )
        .all()
    )
    for task, phase, project in candidate_tasks:
        _, _, is_gov = ctx_for(project)
        effective = derive_effective_status(
            db,
            task=task,
            project=project,
            actor_user_id=user_id,
            is_governor=is_gov,
        )
        if effective != "actionable":
            continue
        if _task_covered_by_queues(task, db, queue_gi_ids):
            continue
        actionable_tasks.append(
            {
                "task_id": task.id,
                "task_title": task.title,
                "project_id": project.id,
                "project_name": project.name,
                "phase_name": phase.name,
                "effective_status": effective,
            }
        )

    return {
        "submit": submit,
        "sign": sign,
        "actionable_tasks": actionable_tasks,
        "ready_tasks": actionable_tasks,
        "deviation_actions": deviation_actions,
    }
