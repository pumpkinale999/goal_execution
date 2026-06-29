"""Phase effective window derivation (§4.8.2 · v2.28)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Protocol

from app.constants import SYSTEM_END_PHASE_NAME


class PhaseScheduleLike(Protocol):
    is_system: bool
    sequence: int
    name: str
    planned_start: str | None
    planned_end: str | None


def plan_date_to_ord(value: str) -> int:
    return date.fromisoformat(value).toordinal()


class ProgramPeriodLike(Protocol):
    period_start: str | None
    period_end: str | None
    period_granularity: str | None


class ObjectivePeriodLike(Protocol):
    period_start: str | None
    period_end: str | None
    period_granularity: str | None


def add_plan_days(iso_date: str, days: int) -> str:
    return (date.fromisoformat(iso_date) + timedelta(days=days)).isoformat()


# Inclusive 7 calendar days: Mon..Sun → end = start + 6 (not +7, which spans 8 calendar days).
ONE_WEEK_INCLUSIVE_DAYS = 6


def one_week_end_from_start(start: str) -> str:
    return add_plan_days(start, ONE_WEEK_INCLUSIVE_DAYS)


def one_week_start_from_end(end: str) -> str:
    return add_plan_days(end, -ONE_WEEK_INCLUSIVE_DAYS)


def _has_end_system_phase(sorted_phases: list[PhaseScheduleLike]) -> bool:
    return any(_is_end_system_phase(phase) for phase in sorted_phases)


def _business_phase_default_end(period_end: str, sorted_phases: list[PhaseScheduleLike]) -> str:
    if _has_end_system_phase(sorted_phases):
        return add_plan_days(one_week_start_from_end(period_end), -1)
    return period_end


def build_program_period(
    program: ProgramPeriodLike | None,
    *,
    objective: ObjectivePeriodLike | None = None,
) -> dict[str, Any] | None:
    """Resolved program window: persisted program period, else inherit sub-objective (§3.3.6)."""
    if program is None:
        return None
    start = program.period_start
    end = program.period_end
    gran = program.period_granularity
    if not start or not end:
        if objective and objective.period_start and objective.period_end:
            start = objective.period_start
            end = objective.period_end
            if not gran:
                gran = objective.period_granularity
        else:
            return None
    return {
        "period_start": start,
        "period_end": end,
        "period_granularity": gran,
    }


def program_period_ok(program_period: dict[str, Any] | None) -> bool:
    if not program_period:
        return False
    return bool(program_period.get("period_start") and program_period.get("period_end"))


def _is_start_system_phase(phase: PhaseScheduleLike) -> bool:
    return bool(phase.is_system and phase.sequence == 0)


def _is_end_system_phase(phase: PhaseScheduleLike) -> bool:
    return bool(phase.is_system and phase.name == SYSTEM_END_PHASE_NAME)


def _prev_phase(sorted_phases: list[PhaseScheduleLike], target: PhaseScheduleLike) -> PhaseScheduleLike | None:
    prior = [p for p in sorted_phases if p.sequence < target.sequence]
    if not prior:
        return None
    return max(prior, key=lambda p: p.sequence)


def _prev_effective_end(
    phase: PhaseScheduleLike,
    sorted_phases: list[PhaseScheduleLike],
    program_period: dict[str, Any],
    effective_by_sequence: dict[int, tuple[str | None, str | None, bool]],
) -> str | None:
    prev = _prev_phase(sorted_phases, phase)
    if prev is None:
        return None
    if prev.sequence in effective_by_sequence:
        _start, prev_end, _ = effective_by_sequence[prev.sequence]
        if prev_end:
            return prev_end
        prev_start, _, _ = effective_by_sequence[prev.sequence]
        if prev_start:
            return prev_start
    if prev.planned_end:
        return prev.planned_end
    if prev.planned_start:
        return prev.planned_start
    start_phase = next((p for p in sorted_phases if _is_start_system_phase(p)), None)
    if start_phase is not None and start_phase.sequence in effective_by_sequence:
        _, start_end, _ = effective_by_sequence[start_phase.sequence]
        if start_end:
            return start_end
    return program_period.get("period_start")


def derive_phase_effective_window(
    phases: list[PhaseScheduleLike],
    program_period: dict[str, Any] | None,
    *,
    target_sequence: int,
) -> tuple[str | None, str | None, bool]:
    """Return (effective_start, effective_end, planned_window_is_derived) for one phase."""
    if not program_period_ok(program_period):
        return None, None, False
    assert program_period is not None

    sorted_phases = sorted(phases, key=lambda p: p.sequence)
    target = next((p for p in sorted_phases if p.sequence == target_sequence), None)
    if target is None:
        return None, None, False

    effective_by_sequence: dict[int, tuple[str | None, str | None, bool]] = {}
    for phase in sorted_phases:
        if phase.sequence > target_sequence:
            break
        effective_by_sequence[phase.sequence] = _compute_phase_effective(
            phase, sorted_phases, program_period, effective_by_sequence
        )
    return effective_by_sequence[target.sequence]


def _compute_phase_effective(
    phase: PhaseScheduleLike,
    sorted_phases: list[PhaseScheduleLike],
    program_period: dict[str, Any],
    effective_by_sequence: dict[int, tuple[str | None, str | None, bool]],
) -> tuple[str | None, str | None, bool]:
    period_start = str(program_period["period_start"])
    period_end = str(program_period["period_end"])
    ps = phase.planned_start
    pe = phase.planned_end

    if ps and pe:
        return ps, pe, False

    eff_start = ps
    eff_end = pe

    if _is_start_system_phase(phase):
        if not eff_start:
            eff_start = period_start
        if not eff_end:
            eff_end = one_week_end_from_start(eff_start)
    elif _is_end_system_phase(phase):
        if not eff_end:
            eff_end = period_end
        if not eff_start:
            eff_start = one_week_start_from_end(eff_end)
    else:
        prev_end = _prev_effective_end(phase, sorted_phases, program_period, effective_by_sequence)
        if not eff_start:
            if not prev_end:
                return None, None, False
            eff_start = add_plan_days(prev_end, 1)
        if not eff_end:
            eff_end = _business_phase_default_end(period_end, sorted_phases)

    if eff_start and eff_end and plan_date_to_ord(eff_start) > plan_date_to_ord(eff_end):
        return None, None, False

    is_derived = ps is None and pe is None
    return eff_start, eff_end, is_derived


def enrich_phases_with_effective(
    phases: list[PhaseScheduleLike],
    program_period: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Attach effective_planned_* and planned_window_is_derived to phase dict payloads."""
    sorted_phases = sorted(phases, key=lambda p: p.sequence)
    effective_by_sequence: dict[int, tuple[str | None, str | None, bool]] = {}
    if program_period_ok(program_period):
        assert program_period is not None
        for phase in sorted_phases:
            effective_by_sequence[phase.sequence] = _compute_phase_effective(
                phase, sorted_phases, program_period, effective_by_sequence
            )

    out: list[dict[str, Any]] = []
    for phase in sorted_phases:
        eff_start, eff_end, is_derived = effective_by_sequence.get(phase.sequence, (None, None, False))
        row: dict[str, Any] = {
            "effective_planned_start": eff_start,
            "effective_planned_end": eff_end,
            "planned_window_is_derived": is_derived,
        }
        out.append(row)
    return out


def effective_window_for_phase(
    phase: PhaseScheduleLike,
    phases: list[PhaseScheduleLike],
    program_period: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    """Effective window for validation (GI due, schedule checks)."""
    eff_start, eff_end, _ = derive_phase_effective_window(
        phases, program_period, target_sequence=phase.sequence
    )
    if eff_start and eff_end:
        return eff_start, eff_end
    return phase.planned_start, phase.planned_end
