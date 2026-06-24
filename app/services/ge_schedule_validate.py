"""Plan schedule validation for Phase and GateItem (§4.8)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Protocol

from fastapi import HTTPException

from app.constants import SYSTEM_END_PHASE_NAME

PLAN_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TASK_SCHEDULE_KEYS = frozenset({"planned_start", "planned_end", "planned_due"})


class PhaseScheduleLike(Protocol):
    is_system: bool
    sequence: int
    name: str
    planned_start: str | None
    planned_end: str | None


def parse_plan_date(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    text = str(value).strip()
    if not PLAN_DATE_RE.match(text):
        raise HTTPException(status_code=400, detail={"detail": "invalid_plan_date"})
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"detail": "invalid_plan_date"}) from exc
    return text


def parse_required_plan_date(value: Any, *, field: str) -> str:
    parsed = parse_plan_date(value, field=field)
    if parsed is None:
        raise HTTPException(status_code=400, detail={"detail": "gate_item_planned_due_required"})
    return parsed


def plan_date_to_ord(value: str) -> int:
    return date.fromisoformat(value).toordinal()


def validate_phase_window(planned_start: str | None, planned_end: str | None) -> None:
    if planned_start is None and planned_end is None:
        return
    if planned_start is None or planned_end is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_phase_window"})
    if plan_date_to_ord(planned_start) > plan_date_to_ord(planned_end):
        raise HTTPException(status_code=400, detail={"detail": "invalid_phase_window"})


def require_business_phase_window(planned_start: str | None, planned_end: str | None) -> None:
    """Canvas add/patch business phase: both planned dates required."""
    if planned_start is None or planned_end is None:
        raise HTTPException(status_code=400, detail={"detail": "phase_planned_window_required"})
    validate_phase_window(planned_start, planned_end)


def validate_gate_item_due_in_phase(
    planned_due: str | None,
    *,
    phase_planned_start: str | None,
    phase_planned_end: str | None,
) -> None:
    if planned_due is None:
        return
    if phase_planned_start is None or phase_planned_end is None:
        return
    due_ord = plan_date_to_ord(planned_due)
    if due_ord < plan_date_to_ord(phase_planned_start) or due_ord > plan_date_to_ord(phase_planned_end):
        raise HTTPException(status_code=400, detail={"detail": "gate_item_schedule_outside_phase"})


def _start_system_phase(phases: list[PhaseScheduleLike]) -> PhaseScheduleLike | None:
    return next((phase for phase in phases if phase.is_system and phase.sequence == 0), None)


def _end_system_phase(phases: list[PhaseScheduleLike]) -> PhaseScheduleLike | None:
    return next((phase for phase in phases if phase.is_system and phase.name == SYSTEM_END_PHASE_NAME), None)


def validate_project_schedule(phases: list[PhaseScheduleLike]) -> None:
    """Start/End system phases define project bounds; business phases must fit inside."""
    for phase in phases:
        validate_phase_window(phase.planned_start, phase.planned_end)

    start = _start_system_phase(phases)
    end = _end_system_phase(phases)
    if (
        start
        and start.planned_start
        and start.planned_end
        and end
        and end.planned_start
        and end.planned_end
    ):
        start_ord = plan_date_to_ord(start.planned_start)
        end_ord = plan_date_to_ord(end.planned_end)
        if start_ord > end_ord:
            raise HTTPException(status_code=400, detail={"detail": "invalid_project_schedule"})
        if plan_date_to_ord(start.planned_end) > end_ord:
            raise HTTPException(status_code=400, detail={"detail": "invalid_project_schedule"})
        if plan_date_to_ord(end.planned_start) < start_ord:
            raise HTTPException(status_code=400, detail={"detail": "invalid_project_schedule"})

        project_start = start.planned_start
        project_end = end.planned_end
        for phase in phases:
            if phase.is_system or phase.planned_start is None or phase.planned_end is None:
                continue
            if plan_date_to_ord(phase.planned_start) < plan_date_to_ord(project_start):
                raise HTTPException(status_code=400, detail={"detail": "phase_schedule_outside_project"})
            if plan_date_to_ord(phase.planned_end) > plan_date_to_ord(project_end):
                raise HTTPException(status_code=400, detail={"detail": "phase_schedule_outside_project"})


def reject_task_schedule_fields(body: dict[str, Any]) -> None:
    if TASK_SCHEDULE_KEYS.intersection(body.keys()):
        raise HTTPException(status_code=400, detail={"detail": "unsupported_task_schedule_field"})
