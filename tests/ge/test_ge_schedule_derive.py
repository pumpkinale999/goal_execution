"""GE-T158-A · Unit tests for ge_schedule_derive (§4.8.2)."""

from __future__ import annotations

from types import SimpleNamespace

from app.constants import SYSTEM_END_PHASE_NAME, SYSTEM_START_PHASE_NAME
from app.services.ge_schedule_derive import (
    add_plan_days,
    build_program_period,
    derive_phase_effective_window,
    enrich_phases_with_effective,
    one_week_end_from_start,
    one_week_start_from_end,
)

PROGRAM = {
    "period_start": "2026-04-01",
    "period_end": "2026-06-30",
    "period_granularity": "quarter",
}


def test_one_week_inclusive_calendar_days():
    """One week = 7 calendar days inclusive (start + 6), not start + 7 (8 days)."""
    assert one_week_end_from_start("2026-04-01") == "2026-04-07"
    assert one_week_start_from_end("2026-06-30") == "2026-06-24"


def _phase(*, sequence: int, name: str, is_system: bool = False, ps=None, pe=None):
    return SimpleNamespace(
        sequence=sequence,
        name=name,
        is_system=is_system,
        planned_start=ps,
        planned_end=pe,
    )


def _chain():
    return [
        _phase(sequence=0, name=SYSTEM_START_PHASE_NAME, is_system=True),
        _phase(sequence=1, name="方案"),
        _phase(sequence=2, name=SYSTEM_END_PHASE_NAME, is_system=True),
    ]


def test_derive_start_from_program():
    phases = _chain()
    start, end, derived = derive_phase_effective_window(phases, PROGRAM, target_sequence=0)
    assert start == "2026-04-01"
    assert end == "2026-04-07"
    assert end == one_week_end_from_start(start)
    assert derived is True


def test_derive_business_from_prev_plus_one():
    phases = _chain()
    start, end, derived = derive_phase_effective_window(phases, PROGRAM, target_sequence=1)
    assert start == "2026-04-08"
    assert end == "2026-06-23"
    assert derived is True


def test_derive_end_one_week():
    phases = _chain()
    start, end, derived = derive_phase_effective_window(phases, PROGRAM, target_sequence=2)
    assert end == "2026-06-30"
    assert start == "2026-06-24"
    assert start == one_week_start_from_end(end)
    assert derived is True


def test_derive_prev_end_fallback_chain():
    """Business phase with only planned_start derives end from program period_end."""
    phases = [
        _phase(sequence=0, name=SYSTEM_START_PHASE_NAME, is_system=True, ps="2026-04-01", pe="2026-04-07"),
        _phase(sequence=1, name="方案", ps="2026-05-01"),
    ]
    s1, e1, derived1 = derive_phase_effective_window(phases, PROGRAM, target_sequence=1)
    assert s1 == "2026-05-01"
    assert e1 == "2026-06-30"
    assert derived1 is False


def test_derive_partial_persisted():
    phases = [
        _phase(sequence=0, name=SYSTEM_START_PHASE_NAME, is_system=True, ps="2026-04-01", pe="2026-04-15"),
        _phase(sequence=1, name="方案", ps="2026-04-20"),
    ]
    start, end, derived = derive_phase_effective_window(phases, PROGRAM, target_sequence=1)
    assert start == "2026-04-20"
    assert end == "2026-06-30"
    assert derived is False


def test_derive_no_program_period():
    phases = _chain()
    start, end, derived = derive_phase_effective_window(phases, None, target_sequence=0)
    assert start is None
    assert end is None
    assert derived is False


def test_effective_equals_planned_when_full():
    phases = [
        _phase(
            sequence=1,
            name="开发",
            ps="2026-05-01",
            pe="2026-05-31",
        ),
    ]
    start, end, derived = derive_phase_effective_window(phases, PROGRAM, target_sequence=1)
    assert start == "2026-05-01"
    assert end == "2026-05-31"
    assert derived is False


def test_enrich_phases_with_effective():
    phases = _chain()
    rows = enrich_phases_with_effective(phases, PROGRAM)
    assert len(rows) == 3
    assert rows[0]["planned_window_is_derived"] is True
    assert rows[0]["effective_planned_start"] == "2026-04-01"
    assert rows[1]["effective_planned_start"] == "2026-04-08"


def test_build_program_period_inherits_from_objective():
    program = SimpleNamespace(period_start=None, period_end=None, period_granularity="quarter")
    objective = SimpleNamespace(
        period_start="2026-04-01",
        period_end="2026-06-30",
        period_granularity="quarter",
    )
    resolved = build_program_period(program, objective=objective)
    assert resolved == {
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
        "period_granularity": "quarter",
    }
