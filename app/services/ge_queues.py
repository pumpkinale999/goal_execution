"""Execution queues (§4.4 · M23 actionable_tasks)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ge import GeDeviation, GeGateItem, GePhase, GeProject, GeTask, GeTaskGateItemProduce
from app.services.ge_deviations import build_deviation_actions_for_user
from app.services.ge_effective_status import derive_effective_status
from app.services.ge_graph import _produce_gate_item_ids, eligible_signers


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


def build_queues(db: Session, user_id: str) -> dict:
    submit: list[dict] = []
    sign: list[dict] = []
    actionable_tasks: list[dict] = []
    deviation_actions = build_deviation_actions_for_user(db, user_id)

    active_projects = db.query(GeProject).filter(GeProject.status == "active", GeProject.deleted_at.is_(None)).all()
    project_map = {p.id: p for p in active_projects}

    produce_rows = (
        db.query(GeTaskGateItemProduce, GeTask, GeGateItem, GePhase)
        .join(GeTask, GeTask.id == GeTaskGateItemProduce.task_id)
        .join(GeGateItem, GeGateItem.id == GeTaskGateItemProduce.gate_item_id)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .filter(GeTask.assignee_user_id == user_id)
        .all()
    )
    for _, task, item, phase in produce_rows:
        project = project_map.get(task.project_id)
        if project is None:
            continue
        if item.status in ("draft", "rejected"):
            submit.append(
                {
                    "gate_item_id": item.id,
                    "gate_item_name": item.name,
                    "project_id": project.id,
                    "project_name": project.name,
                    "phase_name": phase.name,
                }
            )
        elif item.status == "deviation":
            dev = (
                db.query(GeDeviation)
                .filter(
                    GeDeviation.gate_item_id == item.id,
                    GeDeviation.status == "active",
                )
                .first()
            )
            if dev is not None:
                submit.append(
                    {
                        "gate_item_id": item.id,
                        "gate_item_name": item.name,
                        "project_id": project.id,
                        "project_name": project.name,
                        "phase_name": phase.name,
                    }
                )

    pending_items = (
        db.query(GeGateItem, GePhase, GeProject)
        .join(GePhase, GePhase.id == GeGateItem.phase_id)
        .join(GeProject, GeProject.id == GePhase.project_id)
        .filter(GeGateItem.status == "pending_sign", GeProject.status == "active", GeProject.deleted_at.is_(None))
        .all()
    )
    for item, phase, project in pending_items:
        if user_id in eligible_signers(db, item.id):
            sign.append(
                {
                    "gate_item_id": item.id,
                    "gate_item_name": item.name,
                    "project_id": project.id,
                    "project_name": project.name,
                    "phase_name": phase.name,
                    "submitted_by_user_id": item.submitted_by,
                }
            )

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
        is_governor = user_id == project.pm_user_id
        effective = derive_effective_status(
            db,
            task=task,
            project=project,
            actor_user_id=user_id,
            is_governor=is_governor,
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
