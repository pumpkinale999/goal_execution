"""M23 B′ · read-time Task effective_status (《需求》§4.6.2)."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.ge import GeDeviation, GeGateItem, GePhase, GeProject, GeTask
from app.services.ge_graph import (
    _prerequisite_gate_item_ids,
    _produce_gate_item_ids,
    eligible_signers,
    task_can_start,
)

EffectiveStatus = Literal["waiting", "actionable", "complete", "deviated"]


def actor_is_governor(project: GeProject, actor_user_id: str, *, is_governor: bool) -> bool:
    if is_governor:
        return True
    return actor_user_id == project.pm_user_id


def actor_can_act_as_task_assignee(
    project: GeProject,
    task: GeTask,
    actor_user_id: str,
    *,
    is_governor: bool,
) -> bool:
    if task.assignee_user_id == actor_user_id:
        return True
    return actor_is_governor(project, actor_user_id, is_governor=is_governor)


def actor_can_act_as_signer(
    db: Session,
    project: GeProject,
    gate_item_id: str,
    actor_user_id: str,
    *,
    is_governor: bool,
) -> bool:
    if actor_user_id in eligible_signers(db, gate_item_id):
        return True
    return actor_is_governor(project, actor_user_id, is_governor=is_governor)


def can_progress(db: Session, task: GeTask, project: GeProject, phase: GePhase | None) -> bool:
    if project.status != "active":
        return False
    if task.status == "deviated":
        return False
    if phase is None:
        phase = db.get(GePhase, task.phase_id)
    if phase is None:
        return False
    return task_can_start(db, task, phase)


def derive_effective_status(
    db: Session,
    *,
    task: GeTask,
    project: GeProject,
    actor_user_id: str,
    is_governor: bool = False,
) -> EffectiveStatus:
    if task.status == "deviated":
        return "deviated"

    produce_ids = _produce_gate_item_ids(db, task.id)
    prereq_ids = _prerequisite_gate_item_ids(db, task.id)

    if produce_ids:
        return _derive_produce_task_status(
            db,
            task=task,
            project=project,
            actor_user_id=actor_user_id,
            is_governor=is_governor,
            produce_ids=produce_ids,
        )

    if prereq_ids:
        return _derive_sign_route_task_status(
            db,
            project=project,
            actor_user_id=actor_user_id,
            is_governor=is_governor,
            prereq_ids=prereq_ids,
        )

    return "waiting"


def _derive_produce_task_status(
    db: Session,
    *,
    task: GeTask,
    project: GeProject,
    actor_user_id: str,
    is_governor: bool,
    produce_ids: list[str],
) -> EffectiveStatus:
    items = [db.get(GeGateItem, gi_id) for gi_id in produce_ids]
    items = [gi for gi in items if gi is not None]
    if items and all(gi.status == "signed" for gi in items):
        return "complete"

    phase = db.get(GePhase, task.phase_id)
    if not can_progress(db, task, project, phase):
        return "waiting"

    if any(gi.status in ("draft", "rejected") for gi in items):
        if actor_can_act_as_task_assignee(project, task, actor_user_id, is_governor=is_governor):
            return "actionable"
        return "waiting"

    for gi in items:
        if gi.status == "deviation":
            dev = (
                db.query(GeDeviation)
                .filter(
                    GeDeviation.gate_item_id == gi.id,
                    GeDeviation.status == "active",
                )
                .first()
            )
            if dev is not None and task.deviation_id is not None:
                if actor_can_act_as_task_assignee(project, task, actor_user_id, is_governor=is_governor):
                    return "actionable"
                return "waiting"

    return "waiting"


def _derive_sign_route_task_status(
    db: Session,
    *,
    project: GeProject,
    actor_user_id: str,
    is_governor: bool,
    prereq_ids: list[str],
) -> EffectiveStatus:
    items = [db.get(GeGateItem, gi_id) for gi_id in prereq_ids]
    items = [gi for gi in items if gi is not None]
    if items and all(gi.status == "signed" for gi in items):
        return "complete"

    for gi in items:
        if gi.status == "pending_sign":
            if actor_can_act_as_signer(db, project, gi.id, actor_user_id, is_governor=is_governor):
                return "actionable"

    return "waiting"


def attach_effective_status_to_graph(
    db: Session,
    graph: dict[str, Any],
    *,
    actor_user_id: str,
    is_governor: bool = False,
) -> dict[str, Any]:
    project_row = db.get(GeProject, graph["project"]["id"])
    if project_row is None:
        return graph

    task_rows = {
        t.id: t
        for t in db.query(GeTask).filter(GeTask.project_id == project_row.id).all()
    }

    for phase in graph.get("phases", []):
        for task_dict in phase.get("tasks", []):
            task_row = task_rows.get(task_dict["id"])
            if task_row is None:
                continue
            task_dict["effective_status"] = derive_effective_status(
                db,
                task=task_row,
                project=project_row,
                actor_user_id=actor_user_id,
                is_governor=is_governor,
            )
    return graph


def effective_status_for_task_row(
    db: Session,
    *,
    task: GeTask,
    project: GeProject,
    actor_user_id: str,
    is_governor: bool = False,
) -> EffectiveStatus:
    return derive_effective_status(
        db,
        task=task,
        project=project,
        actor_user_id=actor_user_id,
        is_governor=is_governor,
    )
