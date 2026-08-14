"""Stock project graph migration: rename system GIs; backfill empty shells."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.constants import (
    LEGACY_SYSTEM_END_GATE_ITEM_NAME,
    LEGACY_SYSTEM_START_GATE_ITEM_NAME,
    PROPOSAL_GATE_ITEM_NAME,
    PROPOSAL_PHASE_NAME,
    PROPOSAL_RESEARCH_TASK_TITLE,
    PROPOSAL_REVIEW_TASK_TITLE,
    SAMPLE_PHASE_NAME,
    SYSTEM_END_GATE_ITEM_NAME,
    SYSTEM_END_PHASE_NAME,
    SYSTEM_END_SIGN_TASK_TITLE,
    SYSTEM_END_TASK_TITLE,
    SYSTEM_START_GATE_ITEM_NAME,
    SYSTEM_START_PHASE_NAME,
    SYSTEM_START_TASK_TITLE,
    TASK_STATUS_IDLE,
)
from app.models.ge import (
    GeGate,
    GeGateItem,
    GePhase,
    GeProject,
    GeTask,
)
from app.services.ge_default_proposal import PROPOSAL_SOLUTION_KEY
from app.services.ge_gate_includes_sync import sync_gate_includes_for_phase
from app.services.ge_graph import now_iso
from app.services.ge_schedule_validate import midpoint_plan_date
from app.services.ge_system_tasks import _ensure_prerequisite_link, _ensure_produce_link

ActionKind = Literal["shell_backfill", "rename_only", "skip_anomaly", "noop"]

_PROGRESS_STATUSES = frozenset({"pending_sign", "signed", "submitted"})
_SHELL_MIDDLE_NAMES = frozenset({PROPOSAL_PHASE_NAME, SAMPLE_PHASE_NAME})


@dataclass
class ProjectMigrationPlan:
    project_id: str
    project_name: str
    action: ActionKind
    reason: str
    rename_start: bool = False
    rename_end: bool = False
    insert_proposal: bool = False
    fill_proposal: bool = False


def _phases(db: Session, project_id: str) -> list[GePhase]:
    return (
        db.query(GePhase)
        .filter(GePhase.project_id == project_id)
        .order_by(GePhase.sequence)
        .all()
    )


def _system_gi_has_progress(db: Session, phase_ids: list[str]) -> bool:
    if not phase_ids:
        return False
    rows = (
        db.query(GeGateItem)
        .filter(GeGateItem.phase_id.in_(phase_ids), GeGateItem.is_system.is_(True))
        .all()
    )
    return any(str(gi.status or "") in _PROGRESS_STATUSES for gi in rows)


def _has_lifecycle_skeleton(db: Session, start: GePhase | None, end: GePhase | None) -> bool:
    if start is None or end is None:
        return False
    start_task = (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == start.id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_START_TASK_TITLE,
        )
        .first()
    )
    end_task = (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == end.id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_END_TASK_TITLE,
        )
        .first()
    )
    end_sign = (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == end.id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_END_SIGN_TASK_TITLE,
        )
        .first()
    )
    return start_task is not None and end_task is not None and end_sign is not None


def classify_project(db: Session, project: GeProject) -> ProjectMigrationPlan:
    phases = _phases(db, project.id)
    start = next((p for p in phases if p.is_system and p.name == SYSTEM_START_PHASE_NAME), None)
    end = next((p for p in phases if p.is_system and p.name == SYSTEM_END_PHASE_NAME), None)
    middle = [p for p in phases if not p.is_system]

    rename_start = False
    rename_end = False
    if start is not None:
        gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == start.id, GeGateItem.is_system.is_(True))
            .first()
        )
        if gi is not None and gi.name == LEGACY_SYSTEM_START_GATE_ITEM_NAME:
            rename_start = True
        elif gi is not None and gi.name != SYSTEM_START_GATE_ITEM_NAME:
            return ProjectMigrationPlan(
                project.id, project.name, "skip_anomaly", f"start_gi_name={gi.name}"
            )
    if end is not None:
        gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == end.id, GeGateItem.is_system.is_(True))
            .first()
        )
        if gi is not None and gi.name == LEGACY_SYSTEM_END_GATE_ITEM_NAME:
            rename_end = True
        elif gi is not None and gi.name != SYSTEM_END_GATE_ITEM_NAME:
            return ProjectMigrationPlan(
                project.id, project.name, "skip_anomaly", f"end_gi_name={gi.name}"
            )

    if start is None or end is None:
        return ProjectMigrationPlan(
            project.id,
            project.name,
            "skip_anomaly",
            "missing_system_start_or_end",
            rename_start=rename_start,
            rename_end=rename_end,
        )

    if not _has_lifecycle_skeleton(db, start, end):
        return ProjectMigrationPlan(
            project.id,
            project.name,
            "skip_anomaly",
            "missing_lifecycle_tasks",
            rename_start=rename_start,
            rename_end=rename_end,
        )

    system_phase_ids = [start.id, end.id]
    if _system_gi_has_progress(db, system_phase_ids):
        action: ActionKind = "rename_only" if (rename_start or rename_end) else "noop"
        return ProjectMigrationPlan(
            project.id,
            project.name,
            action,
            "system_gi_progress",
            rename_start=rename_start,
            rename_end=rename_end,
        )

    if len(middle) > 1:
        action = "rename_only" if (rename_start or rename_end) else "noop"
        return ProjectMigrationPlan(
            project.id,
            project.name,
            action,
            "multiple_middle_phases",
            rename_start=rename_start,
            rename_end=rename_end,
        )

    if len(middle) == 1:
        phase = middle[0]
        if phase.name.strip() not in _SHELL_MIDDLE_NAMES:
            action = "rename_only" if (rename_start or rename_end) else "noop"
            return ProjectMigrationPlan(
                project.id,
                project.name,
                action,
                f"middle_name={phase.name}",
                rename_start=rename_start,
                rename_end=rename_end,
            )
        has_task = db.query(GeTask).filter(GeTask.phase_id == phase.id).first() is not None
        has_gi = db.query(GeGateItem).filter(GeGateItem.phase_id == phase.id).first() is not None
        if has_task or has_gi:
            has_solution = (
                db.query(GeGateItem)
                .filter(GeGateItem.phase_id == phase.id, GeGateItem.name == PROPOSAL_GATE_ITEM_NAME)
                .first()
                is not None
            )
            has_research = (
                db.query(GeTask)
                .filter(GeTask.phase_id == phase.id, GeTask.title == PROPOSAL_RESEARCH_TASK_TITLE)
                .first()
                is not None
            )
            if has_solution and has_research:
                action = "rename_only" if (rename_start or rename_end) else "noop"
                return ProjectMigrationPlan(
                    project.id,
                    project.name,
                    action,
                    "proposal_already_filled",
                    rename_start=rename_start,
                    rename_end=rename_end,
                )
            action = "rename_only" if (rename_start or rename_end) else "noop"
            return ProjectMigrationPlan(
                project.id,
                project.name,
                action,
                "has_business_nodes",
                rename_start=rename_start,
                rename_end=rename_end,
            )
        return ProjectMigrationPlan(
            project.id,
            project.name,
            "shell_backfill",
            "empty_shell_middle",
            rename_start=rename_start,
            rename_end=rename_end,
            insert_proposal=False,
            fill_proposal=True,
        )

    # No middle phase
    return ProjectMigrationPlan(
        project.id,
        project.name,
        "shell_backfill",
        "empty_shell_no_middle",
        rename_start=rename_start,
        rename_end=rename_end,
        insert_proposal=True,
        fill_proposal=True,
    )


def _rename_system_gis(db: Session, project_id: str, plan: ProjectMigrationPlan, *, now: str) -> int:
    changed = 0
    phases = _phases(db, project_id)
    start = next((p for p in phases if p.is_system and p.name == SYSTEM_START_PHASE_NAME), None)
    end = next((p for p in phases if p.is_system and p.name == SYSTEM_END_PHASE_NAME), None)
    if plan.rename_start and start is not None:
        gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == start.id, GeGateItem.is_system.is_(True))
            .first()
        )
        if gi is not None and gi.name == LEGACY_SYSTEM_START_GATE_ITEM_NAME:
            gi.name = SYSTEM_START_GATE_ITEM_NAME
            gi.updated_at = now
            changed += 1
    if plan.rename_end and end is not None:
        gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == end.id, GeGateItem.is_system.is_(True))
            .first()
        )
        if gi is not None and gi.name == LEGACY_SYSTEM_END_GATE_ITEM_NAME:
            gi.name = SYSTEM_END_GATE_ITEM_NAME
            gi.updated_at = now
            changed += 1
    return changed


def _ensure_proposal_phase(db: Session, project: GeProject, *, now: str) -> GePhase:
    phases = _phases(db, project.id)
    start = next(p for p in phases if p.is_system and p.name == SYSTEM_START_PHASE_NAME)
    end = next(p for p in phases if p.is_system and p.name == SYSTEM_END_PHASE_NAME)
    middle = [p for p in phases if not p.is_system]
    if middle:
        phase = middle[0]
        if phase.name != PROPOSAL_PHASE_NAME:
            phase.name = PROPOSAL_PHASE_NAME
            phase.updated_at = now
        if start.planned_start and end.planned_start:
            if not phase.planned_start:
                phase.planned_start = start.planned_start
            if not phase.planned_end:
                phase.planned_end = end.planned_start
            phase.updated_at = now
        return phase

    # Insert between start and end: shift end sequence
    end.sequence = start.sequence + 2
    end.updated_at = now
    phase_id = str(uuid.uuid4())
    planned_start = start.planned_start
    planned_end = end.planned_start
    phase = GePhase(
        id=phase_id,
        project_id=project.id,
        sequence=start.sequence + 1,
        name=PROPOSAL_PHASE_NAME,
        status="pending",
        is_system=False,
        planned_start=planned_start,
        planned_end=planned_end,
        created_at=now,
        updated_at=now,
    )
    db.add(phase)
    db.add(GeGate(id=str(uuid.uuid4()), phase_id=phase_id))
    db.flush()
    return phase


def _fill_proposal_content(
    db: Session,
    project: GeProject,
    phase: GePhase,
    *,
    now: str,
) -> None:
    from app.services.ge_gate_item_payload import definition_from_body, parse_form

    solution = (
        db.query(GeGateItem)
        .filter(GeGateItem.phase_id == phase.id, GeGateItem.name == PROPOSAL_GATE_ITEM_NAME)
        .first()
    )
    due = None
    if phase.planned_start and phase.planned_end:
        due = midpoint_plan_date(phase.planned_start, phase.planned_end)
    if solution is None:
        gi_id = str(uuid.uuid4())
        form = parse_form("material")
        definition = definition_from_body(form, {"key": PROPOSAL_SOLUTION_KEY, "name": PROPOSAL_GATE_ITEM_NAME})
        solution = GeGateItem(
            id=gi_id,
            phase_id=phase.id,
            name=PROPOSAL_GATE_ITEM_NAME,
            form=form,
            status="draft",
            planned_due=due,
            created_at=now,
            updated_at=now,
        )
        solution.payload_dict = definition
        db.add(solution)
        db.flush()
        sync_gate_includes_for_phase(db, phase.id)
    elif solution.planned_due is None and due is not None:
        solution.planned_due = due
        solution.updated_at = now

    research = (
        db.query(GeTask)
        .filter(GeTask.phase_id == phase.id, GeTask.title == PROPOSAL_RESEARCH_TASK_TITLE)
        .first()
    )
    if research is None:
        research = GeTask(
            id=str(uuid.uuid4()),
            project_id=project.id,
            phase_id=phase.id,
            assignee_user_id=project.pm_user_id,
            title=PROPOSAL_RESEARCH_TASK_TITLE,
            status=TASK_STATUS_IDLE,
            canvas_order=0,
            created_at=now,
            updated_at=now,
        )
        db.add(research)

    review = (
        db.query(GeTask)
        .filter(GeTask.phase_id == phase.id, GeTask.title == PROPOSAL_REVIEW_TASK_TITLE)
        .first()
    )
    if review is None:
        review = GeTask(
            id=str(uuid.uuid4()),
            project_id=project.id,
            phase_id=phase.id,
            assignee_user_id=project.pm_user_id,
            title=PROPOSAL_REVIEW_TASK_TITLE,
            status=TASK_STATUS_IDLE,
            canvas_order=1,
            created_at=now,
            updated_at=now,
        )
        db.add(review)

    db.flush()
    _ensure_produce_link(db, review.id, solution.id)

    start = next(
        p
        for p in _phases(db, project.id)
        if p.is_system and p.name == SYSTEM_START_PHASE_NAME
    )
    end = next(
        p for p in _phases(db, project.id) if p.is_system and p.name == SYSTEM_END_PHASE_NAME
    )
    start_gi = (
        db.query(GeGateItem)
        .filter(GeGateItem.phase_id == start.id, GeGateItem.is_system.is_(True))
        .first()
    )
    end_produce = (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == end.id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_END_TASK_TITLE,
        )
        .first()
    )
    if start_gi is not None:
        _ensure_prerequisite_link(db, research.id, start_gi.id)
    if end_produce is not None:
        _ensure_prerequisite_link(db, end_produce.id, solution.id)


def apply_project_plan(db: Session, project: GeProject, plan: ProjectMigrationPlan) -> dict[str, Any]:
    now = now_iso()
    result: dict[str, Any] = {
        "project_id": project.id,
        "action": plan.action,
        "reason": plan.reason,
        "renamed": 0,
        "proposal": False,
    }
    if plan.action == "skip_anomaly":
        return result
    if plan.action == "noop":
        return result

    result["renamed"] = _rename_system_gis(db, project.id, plan, now=now)

    if plan.action == "shell_backfill" and plan.fill_proposal:
        phase = _ensure_proposal_phase(db, project, now=now)
        _fill_proposal_content(db, project, phase, now=now)
        result["proposal"] = True

    return result


def plan_all_projects(db: Session, *, project_id: str | None = None) -> list[ProjectMigrationPlan]:
    q = db.query(GeProject).filter(GeProject.deleted_at.is_(None))
    if project_id:
        q = q.filter(GeProject.id == project_id)
    plans: list[ProjectMigrationPlan] = []
    for project in q.order_by(GeProject.created_at).all():
        plans.append(classify_project(db, project))
    return plans
