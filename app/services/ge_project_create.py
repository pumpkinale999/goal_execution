"""Atomic project graph creation (§4.2.2 · Canvas v2)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.constants import (
    PROPOSAL_GATE_ITEM_NAME,
    PROPOSAL_RESEARCH_TASK_TITLE,
    SYSTEM_END_PHASE_NAME,
    SYSTEM_END_TASK_TITLE,
    SYSTEM_START_PHASE_NAME,
    TASK_STATUS_IDLE,
)
from app.models.ge import (
    GeGate,
    GeGateItem,
    GePhase,
    GeProgram,
    GeProject,
    GeTask,
    GeTaskGateItemPrerequisite,
    GeTaskGateItemProduce,
)
from app.services.ge_access import can_create_project
from app.services.ge_default_proposal import PROPOSAL_SOLUTION_KEY, normalize_business_phases_for_create
from app.services.ge_gate_includes_sync import sync_gate_includes_for_phase
from app.services.ge_graph import now_iso, record_audit, recompute_gate_and_phases, recompute_task_status
from app.services.ge_graph_validate import validate_phases_body, validate_project_graph_db
from app.services.ge_schedule_validate import (
    parse_plan_date,
    parse_required_plan_date,
    plan_date_to_ord,
    validate_gate_item_due_in_phase,
    validate_phase_window,
)
from app.services.ge_sort_order import next_project_sort_order
from app.services.ge_strategic_lifecycle import invalidate_lifecycle_refresh
from app.services.ge_system_tasks import _ensure_prerequisite_link, seed_system_lifecycle_graph


def _parse_lifecycle_dates(body: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return start_start, start_end, end_start, end_end.

    Prefer explicit phase windows. Legacy ``lifecycle_start``/``lifecycle_end``
    expand to same-day bookend windows ``[S,S]`` / ``[E,E]``.
    """
    start_start = parse_plan_date(body.get("start_planned_start"), field="start_planned_start")
    start_end = parse_plan_date(body.get("start_planned_end"), field="start_planned_end")
    end_start = parse_plan_date(body.get("end_planned_start"), field="end_planned_start")
    end_end = parse_plan_date(body.get("end_planned_end"), field="end_planned_end")

    if start_start is None and start_end is None and end_start is None and end_end is None:
        lifecycle_start = parse_plan_date(body.get("lifecycle_start"), field="lifecycle_start")
        lifecycle_end = parse_plan_date(body.get("lifecycle_end"), field="lifecycle_end")
        if lifecycle_start is None or lifecycle_end is None:
            raise HTTPException(status_code=400, detail={"detail": "lifecycle_dates_required"})
        start_start = start_end = lifecycle_start
        end_start = end_end = lifecycle_end

    if start_start is None or start_end is None or end_start is None or end_end is None:
        raise HTTPException(status_code=400, detail={"detail": "lifecycle_dates_required"})
    if plan_date_to_ord(start_start) > plan_date_to_ord(start_end):
        raise HTTPException(status_code=400, detail={"detail": "invalid_start_phase_window"})
    if plan_date_to_ord(end_start) > plan_date_to_ord(end_end):
        raise HTTPException(status_code=400, detail={"detail": "invalid_end_phase_window"})
    if plan_date_to_ord(start_end) > plan_date_to_ord(end_start):
        raise HTTPException(status_code=400, detail={"detail": "invalid_lifecycle_window"})
    return start_start, start_end, end_start, end_end


def _wire_default_proposal_cross_phase_prereqs(
    db: Session,
    *,
    project_id: str,
    start_phase_id: str,
    end_phase_id: str,
) -> None:
    """团队共识 → 调研和编写方案；解决方案 → 结项复盘（系统任务）."""
    start_gi = (
        db.query(GeGateItem)
        .filter(GeGateItem.phase_id == start_phase_id, GeGateItem.is_system.is_(True))
        .first()
    )
    solution_gi = (
        db.query(GeGateItem)
        .filter(
            GeGateItem.name == PROPOSAL_GATE_ITEM_NAME,
            GeGateItem.phase_id.in_(
                db.query(GePhase.id).filter(GePhase.project_id == project_id, GePhase.is_system.is_(False))
            ),
        )
        .first()
    )
    research = (
        db.query(GeTask)
        .filter(
            GeTask.project_id == project_id,
            GeTask.title == PROPOSAL_RESEARCH_TASK_TITLE,
            GeTask.is_system.is_(False),
        )
        .first()
    )
    end_produce = (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == end_phase_id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_END_TASK_TITLE,
        )
        .first()
    )
    if start_gi is not None and research is not None:
        _ensure_prerequisite_link(db, research.id, start_gi.id)
    if solution_gi is not None and end_produce is not None:
        _ensure_prerequisite_link(db, end_produce.id, solution_gi.id)


def create_project(
    db: Session,
    *,
    user: AuthUser | None = None,
    actor_user_id: str | None = None,
    body: dict[str, Any],
    commit: bool = True,
) -> dict[str, Any]:
    start_start, start_end, end_start, end_end = _parse_lifecycle_dates(body)
    pm_user_id = str(body.get("pm_user_id") or "").strip()
    if not pm_user_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_assignee"})
    business_phases = normalize_business_phases_for_create(
        body.get("phases"),
        pm_user_id=pm_user_id,
        lifecycle_start=start_start,
        lifecycle_end=end_end,
    )
    deferred_signers = frozenset()
    for phase in business_phases:
        for gi in phase.get("gate_items") or []:
            if gi.get("key") == PROPOSAL_SOLUTION_KEY:
                deferred_signers = frozenset({PROPOSAL_SOLUTION_KEY})
                break
    validate_phases_body(business_phases, deferred_signer_keys=deferred_signers)
    now = now_iso()
    raw_program_id = body.get("program_id")
    if raw_program_id is None or not str(raw_program_id).strip():
        raise HTTPException(status_code=400, detail={"detail": "program_id_required"})
    program_id = str(raw_program_id).strip()
    if db.get(GeProgram, program_id) is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if user is None:
        if not actor_user_id:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        user = AuthUser(user_id=str(actor_user_id), auth_method="service", is_reviewer=False)
    actor_user_id = user.user_id
    if not can_create_project(db, user, program_id=program_id):
        raise HTTPException(status_code=403, detail={"detail": "not_goal_subtree_governor"})
    project_id = str(uuid.uuid4())
    project_note_id = body.get("project_note_id")
    if project_note_id is not None:
        project_note_id = str(project_note_id).strip() or None
    project = GeProject(
        id=project_id,
        program_id=program_id,
        name=str(body["name"]).strip(),
        pm_user_id=pm_user_id,
        created_by_user_id=actor_user_id,
        status="active",
        project_note_id=project_note_id,
        deleted_at=None,
        sort_order=next_project_sort_order(db, program_id),
        created_at=now,
        updated_at=now,
    )
    db.add(project)

    start_phase_id = str(uuid.uuid4())
    db.add(
        GePhase(
            id=start_phase_id,
            project_id=project_id,
            sequence=0,
            name=SYSTEM_START_PHASE_NAME,
            status="active",
            is_system=True,
            planned_start=start_start,
            planned_end=start_end,
            created_at=now,
            updated_at=now,
        )
    )
    start_gate_id = str(uuid.uuid4())
    db.add(GeGate(id=start_gate_id, phase_id=start_phase_id))

    key_to_gate_item_id: dict[str, str] = {}
    pending_produces: list[tuple[str, str]] = []
    pending_prerequisites: list[tuple[str, str]] = []
    task_count = 0
    gate_item_count = 0
    sorted_phases = sorted(business_phases, key=lambda p: p["sequence"])
    phase_id_by_sequence: dict[int, str] = {}
    gate_id_by_sequence: dict[int, str] = {}

    for phase_body in sorted_phases:
        seq = int(phase_body["sequence"])
        phase_id = str(uuid.uuid4())
        phase_id_by_sequence[seq] = phase_id
        planned_start = parse_plan_date(phase_body.get("planned_start"), field="planned_start")
        planned_end = parse_plan_date(phase_body.get("planned_end"), field="planned_end")
        validate_phase_window(planned_start, planned_end)
        db.add(
            GePhase(
                id=phase_id,
                project_id=project_id,
                sequence=seq,
                name=str(phase_body["name"]).strip(),
                status="pending",
                is_system=False,
                planned_start=planned_start,
                planned_end=planned_end,
                created_at=now,
                updated_at=now,
            )
        )
        gate_id = str(uuid.uuid4())
        gate_id_by_sequence[seq] = gate_id
        db.add(GeGate(id=gate_id, phase_id=phase_id))
        for gi_body in phase_body.get("gate_items") or []:
            gi_id = str(uuid.uuid4())
            key_to_gate_item_id[gi_body["key"]] = gi_id
            planned_due = None
            if gi_body.get("planned_due") is not None:
                planned_due = parse_required_plan_date(gi_body.get("planned_due"), field="planned_due")
            validate_gate_item_due_in_phase(
                planned_due,
                phase_planned_start=planned_start,
                phase_planned_end=planned_end,
                gate_item_name=str(gi_body["name"]).strip(),
            )
            from app.services.ge_gate_item_payload import definition_from_body, parse_form

            form = parse_form(gi_body.get("form"))
            def_body = dict(gi_body)
            nested = gi_body.get("payload")
            if isinstance(nested, dict):
                def_body = {**nested, **def_body}
            definition = definition_from_body(form, def_body)
            item = GeGateItem(
                id=gi_id,
                phase_id=phase_id,
                name=str(gi_body["name"]).strip(),
                form=form,
                status="draft",
                planned_due=planned_due,
                created_at=now,
                updated_at=now,
            )
            item.payload_dict = definition
            db.add(item)
            gate_item_count += 1
        sync_gate_includes_for_phase(db, phase_id)
        for task_index, task_body in enumerate(phase_body.get("tasks") or []):
            task_id = str(uuid.uuid4())
            db.add(
                GeTask(
                    id=task_id,
                    project_id=project_id,
                    phase_id=phase_id,
                    assignee_user_id=str(task_body["assignee_user_id"]),
                    title=str(task_body["title"]).strip(),
                    status=TASK_STATUS_IDLE,
                    canvas_order=task_index,
                    created_at=now,
                    updated_at=now,
                )
            )
            task_count += 1
            for key in task_body.get("produces") or []:
                pending_produces.append((task_id, key_to_gate_item_id[key]))
            for key in task_body.get("prerequisites") or []:
                pending_prerequisites.append((task_id, key_to_gate_item_id[key]))

    max_business_seq = max(phase_id_by_sequence.keys()) if phase_id_by_sequence else 0
    end_phase_id = str(uuid.uuid4())
    end_gate_id = str(uuid.uuid4())
    db.add(
        GePhase(
            id=end_phase_id,
            project_id=project_id,
            sequence=max_business_seq + 1,
            name=SYSTEM_END_PHASE_NAME,
            status="pending",
            is_system=True,
            planned_start=end_start,
            planned_end=end_end,
            created_at=now,
            updated_at=now,
        )
    )
    db.add(GeGate(id=end_gate_id, phase_id=end_phase_id))

    # Postgres enforces FKs at flush; link rows must not precede parent tasks/GIs.
    # (SQLite tests often miss this — produce/prereq use bare FK columns, no ORM relationship.)
    db.flush()
    for task_id, gate_item_id in pending_produces:
        db.add(GeTaskGateItemProduce(task_id=task_id, gate_item_id=gate_item_id))
    for task_id, gate_item_id in pending_prerequisites:
        db.add(GeTaskGateItemPrerequisite(task_id=task_id, gate_item_id=gate_item_id))

    system_counts = seed_system_lifecycle_graph(
        db,
        project_id=project_id,
        pm_user_id=pm_user_id,
        start_phase_id=start_phase_id,
        start_gate_id=start_gate_id,
        end_phase_id=end_phase_id,
        end_gate_id=end_gate_id,
        now=now,
        start_phase_planned_start=start_start,
        start_phase_planned_end=start_end,
        end_phase_planned_start=end_start,
        end_phase_planned_end=end_end,
        project_note_id=project_note_id,
    )
    task_count += system_counts["task_count"]
    gate_item_count += system_counts["gate_item_count"]

    db.flush()
    _wire_default_proposal_cross_phase_prereqs(
        db,
        project_id=project_id,
        start_phase_id=start_phase_id,
        end_phase_id=end_phase_id,
    )

    from app.services.ge_project_members import (
        ensure_members_for_project_assignees,
        upsert_pm,
    )

    # Assignees first (member if missing); then force PM role.
    ensure_members_for_project_assignees(db, project_id=project_id)
    upsert_pm(db, project_id=project_id, pm_user_id=pm_user_id)
    db.flush()
    validate_project_graph_db(db, project_id)
    record_audit(
        db,
        actor_user_id=actor_user_id,
        entity_type="project",
        entity_id=project_id,
        action="create",
        payload={"status": "active"},
    )
    recompute_gate_and_phases(db, project_id)
    recompute_task_status(db, project_id)
    if commit:
        db.commit()
        from app.services.observation_mount import notify_graph_write

        notify_graph_write(db, project_id=project_id, change_kind="project_create")
    else:
        db.flush()
    invalidate_lifecycle_refresh()
    return {
        "id": project_id,
        "name": project.name,
        "status": project.status,
        "program_id": project.program_id,
        "pm_user_id": project.pm_user_id,
        "created_by_user_id": project.created_by_user_id,
        "project_note_id": project.project_note_id,
        "graph_summary": {
            "phase_count": len(business_phases) + 2,
            "task_count": task_count,
            "gate_item_count": gate_item_count,
        },
    }
