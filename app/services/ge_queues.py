"""Execution queues (§4.4)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ge import GeDeviation, GeGateItem, GePhase, GeProject, GeTask, GeTaskGateItemProduce
from app.services.ge_deviations import build_deviation_actions_for_user
from app.services.ge_graph import eligible_signers


def build_queues(db: Session, user_id: str) -> dict:
    submit: list[dict] = []
    sign: list[dict] = []
    ready_tasks: list[dict] = []
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

    tasks = (
        db.query(GeTask, GePhase, GeProject)
        .join(GePhase, GePhase.id == GeTask.phase_id)
        .join(GeProject, GeProject.id == GeTask.project_id)
        .filter(
            GeTask.assignee_user_id == user_id,
            GeTask.status == "ready",
            GeProject.status == "active",
            GeProject.deleted_at.is_(None),
        )
        .all()
    )
    for task, phase, project in tasks:
        ready_tasks.append(
            {
                "task_id": task.id,
                "task_title": task.title,
                "project_id": project.id,
                "project_name": project.name,
                "phase_name": phase.name,
            }
        )

    return {
        "submit": submit,
        "sign": sign,
        "ready_tasks": ready_tasks,
        "deviation_actions": deviation_actions,
    }
