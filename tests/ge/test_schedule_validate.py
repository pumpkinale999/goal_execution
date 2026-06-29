"""Unit tests for ge_schedule_validate."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.ge_schedule_validate import (
    parse_plan_date,
    parse_required_plan_date,
    reject_task_schedule_fields,
    require_business_phase_window,
    validate_gate_item_due_in_phase,
    validate_phase_window,
    validate_project_schedule,
)


def test_parse_plan_date_accepts_iso_date():
    assert parse_plan_date("2026-03-01", field="planned_start") == "2026-03-01"


def test_parse_plan_date_rejects_invalid():
    with pytest.raises(HTTPException) as exc:
        parse_plan_date("03/01/2026", field="planned_start")
    assert exc.value.detail == {"detail": "invalid_plan_date"}


def test_validate_phase_window_order():
    validate_phase_window("2026-03-01", "2026-03-15")
    with pytest.raises(HTTPException) as exc:
        validate_phase_window("2026-03-20", "2026-03-01")
    assert exc.value.detail == {"detail": "invalid_phase_window"}


def test_require_business_phase_window():
    require_business_phase_window("2026-03-01", "2026-03-15")
    with pytest.raises(HTTPException) as exc:
        require_business_phase_window(None, "2026-03-15")
    assert exc.value.detail == {"detail": "phase_planned_window_required"}
    with pytest.raises(HTTPException) as exc:
        require_business_phase_window("2026-03-01", None)
    assert exc.value.detail == {"detail": "phase_planned_window_required"}
    with pytest.raises(HTTPException) as exc:
        require_business_phase_window("2026-03-20", "2026-03-01")
    assert exc.value.detail == {"detail": "invalid_phase_window"}


def test_validate_gate_item_due_in_phase_bounds():
    validate_gate_item_due_in_phase(
        "2026-03-10",
        phase_planned_start="2026-03-01",
        phase_planned_end="2026-03-15",
    )
    with pytest.raises(HTTPException) as exc:
        validate_gate_item_due_in_phase(
            "2026-03-20",
            phase_planned_start="2026-03-01",
            phase_planned_end="2026-03-15",
        )
    assert exc.value.detail == {"detail": "gate_item_schedule_outside_phase"}


def test_validate_project_schedule_business_outside_bounds():
    from types import SimpleNamespace

    phases = [
        SimpleNamespace(
            is_system=False,
            sequence=1,
            name="开发",
            planned_start="2027-01-01",
            planned_end="2027-01-31",
        ),
    ]
    program = {"period_start": "2026-01-01", "period_end": "2026-12-31", "period_granularity": "year"}
    with pytest.raises(HTTPException) as exc:
        validate_project_schedule(phases, program_period=program, require_program=True)
    assert exc.value.detail == {"detail": "phase_schedule_outside_program"}


def test_validate_adjacent_overlap():
    from types import SimpleNamespace

    phases = [
        SimpleNamespace(
            is_system=False,
            sequence=1,
            name="A",
            planned_start="2026-06-01",
            planned_end="2026-06-15",
        ),
        SimpleNamespace(
            is_system=False,
            sequence=2,
            name="B",
            planned_start="2026-06-15",
            planned_end="2026-06-30",
        ),
    ]
    with pytest.raises(HTTPException) as exc:
        validate_project_schedule(phases)
    assert exc.value.detail == {"detail": "phase_schedule_overlap"}


def test_parse_required_plan_date():
    with pytest.raises(HTTPException) as exc:
        parse_required_plan_date(None, field="planned_due")
    assert exc.value.detail == {"detail": "gate_item_planned_due_required"}


def test_reject_task_schedule_fields():
    with pytest.raises(HTTPException) as exc:
        reject_task_schedule_fields({"planned_end": "2026-03-01"})
    assert exc.value.detail == {"detail": "unsupported_task_schedule_field"}
