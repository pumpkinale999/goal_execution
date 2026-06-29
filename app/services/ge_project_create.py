"""Atomic project graph creation (§4.2.2 · Canvas v2)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants import SYSTEM_END_PHASE_NAME, SYSTEM_START_PHASE_NAME, TASK_STATUS_IDLE
from app.models.ge import (
    GeGate,
    GeGateItem,
    GePhase,
    GeProject,
    GeTask,
    GeTaskGateItemPrerequisite,
    GeTaskGateItemProduce,
)
from app.services.ge_bootstrap import default_program_id
from app.services.ge_gate_includes_sync import sync_gate_includes_for_phase
from app.services.ge_graph import now_iso, record_audit, recompute_gate_and_phases, recompute_task_status
from app.services.ge_graph_validate import validate_phases_body, validate_project_graph_db
from app.services.ge_schedule_validate import parse_plan_date, parse_required_plan_date, validate_gate_item_due_in_phase, validate_phase_window
from app.services.ge_subtree_governor import is_subtree_governor


def _validate_create_body(body: dict[str, Any]) -> None:
    phases = body.get("phases") or []
    validate_phases_body(phases)
    pm_user_id = body.get("pm_user_id")
    if not pm_user_id or not str(pm_user_id).strip():
        raise HTTPException(status_code=400, detail={"detail": "invalid_assignee"})


def create_project(db: Session, *, actor_user_id: str, body: dict[str, Any], commit: bool = True) -> dict[str, Any]:
    _validate_create_body(body)
    now = now_iso()
    default_pid = default_program_id(db)
    program_id = body.get("program_id") or default_pid
    program_id = str(program_id)
    if "program_id" in body and body.get("program_id") and program_id != default_pid:
        if not is_subtree_governor(db, user_id=actor_user_id, program_id=program_id):
            raise HTTPException(status_code=403, detail={"detail": "not_subtree_governor"})
    project_id = str(uuid.uuid4())
    project_note_id = body.get("project_note_id")
    if project_note_id is not None:
        project_note_id = str(project_note_id).strip() or None
    project = GeProject(
        id=project_id,
        program_id=program_id,
        name=str(body["name"]).strip(),
        pm_user_id=str(body["pm_user_id"]),
        created_by_user_id=actor_user_id,
        status="active",
        project_note_id=project_note_id,
        deleted_at=None,
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
            created_at=now,
            updated_at=now,
        )
    )
    start_gate_id = str(uuid.uuid4())
    db.add(GeGate(id=start_gate_id, phase_id=start_phase_id))

    key_to_gate_item_id: dict[str, str] = {}
    task_count = 0
    gate_item_count = 0
    sorted_phases = sorted(body["phases"], key=lambda p: p["sequence"])
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
            )
            db.add(
                GeGateItem(
                    id=gi_id,
                    phase_id=phase_id,
                    name=str(gi_body["name"]).strip(),
                    form=gi_body["form"],
                    status="draft",
                    payload="{}",
                    planned_due=planned_due,
                    created_at=now,
                    updated_at=now,
                )
            )
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
                db.add(GeTaskGateItemProduce(task_id=task_id, gate_item_id=key_to_gate_item_id[key]))
            for key in task_body.get("prerequisites") or []:
                db.add(
                    GeTaskGateItemPrerequisite(
                        task_id=task_id,
                        gate_item_id=key_to_gate_item_id[key],
                    )
                )

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
            created_at=now,
            updated_at=now,
        )
    )
    db.add(GeGate(id=end_gate_id, phase_id=end_phase_id))

    from app.services.ge_system_tasks import seed_system_lifecycle_graph

    system_counts = seed_system_lifecycle_graph(
        db,
        project_id=project_id,
        pm_user_id=str(body["pm_user_id"]),
        start_phase_id=start_phase_id,
        start_gate_id=start_gate_id,
        end_phase_id=end_phase_id,
        end_gate_id=end_gate_id,
        now=now,
    )
    task_count += system_counts["task_count"]
    gate_item_count += system_counts["gate_item_count"]

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
    else:
        db.flush()
    return {
        "id": project_id,
        "name": project.name,
        "status": project.status,
        "program_id": project.program_id,
        "pm_user_id": project.pm_user_id,
        "created_by_user_id": project.created_by_user_id,
        "project_note_id": project.project_note_id,
        "graph_summary": {
            "phase_count": len(body["phases"]) + 2,
            "task_count": task_count,
            "gate_item_count": gate_item_count,
        },
    }
