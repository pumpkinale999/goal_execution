"""System Start/End phases (Canvas v2 · §4.5)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.constants import SYSTEM_END_PHASE_NAME, SYSTEM_START_PHASE_NAME
from app.models.ge import GeGate, GePhase


def now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_system_phase(phase: GePhase) -> bool:
    return bool(getattr(phase, "is_system", False))


def is_start_phase(phase: GePhase) -> bool:
    return is_system_phase(phase) and phase.sequence == 0


def is_end_phase(phase: GePhase) -> bool:
    if not is_system_phase(phase):
        return False
    end = (
        phase.project.phases[-1]
        if phase.project and phase.project.phases
        else None
    )
    return end is not None and end.id == phase.id


def end_phase_for_project(db: Session, project_id: str) -> GePhase | None:
    return (
        db.query(GePhase)
        .filter(GePhase.project_id == project_id, GePhase.is_system.is_(True))
        .order_by(GePhase.sequence.desc())
        .first()
    )


def business_phases(phases: list[GePhase]) -> list[GePhase]:
    return [p for p in sorted(phases, key=lambda x: x.sequence) if not is_system_phase(p) or p.sequence == 0]


def insert_system_phases(
    db: Session,
    *,
    project_id: str,
    now: str,
    start_status: str = "active",
    end_status: str = "pending",
) -> tuple[GePhase, GePhase]:
    start_id = str(uuid.uuid4())
    end_id = str(uuid.uuid4())
    start = GePhase(
        id=start_id,
        project_id=project_id,
        sequence=0,
        name=SYSTEM_START_PHASE_NAME,
        status=start_status,
        is_system=True,
        created_at=now,
        updated_at=now,
    )
    end = GePhase(
        id=end_id,
        project_id=project_id,
        sequence=0,
        name=SYSTEM_END_PHASE_NAME,
        status=end_status,
        is_system=True,
        created_at=now,
        updated_at=now,
    )
    db.add(start)
    db.add(end)
    db.add(GeGate(id=str(uuid.uuid4()), phase_id=start_id))
    db.add(GeGate(id=str(uuid.uuid4()), phase_id=end_id))
    return start, end


def resequence_with_system_phases(db: Session, project_id: str, business_count: int) -> None:
    """Assign sequence 0=start, 1..n=business, n+1=end after business phases exist."""
    del business_count  # kept for call-site compatibility
    phases = (
        db.query(GePhase)
        .filter(GePhase.project_id == project_id)
        .order_by(GePhase.sequence)
        .all()
    )
    start = next((p for p in phases if p.is_system and p.sequence == 0), None)
    end = next((p for p in phases if p.is_system and p.name == SYSTEM_END_PHASE_NAME), None)
    business = sorted((p for p in phases if not p.is_system), key=lambda p: p.sequence)

    # UNIQUE(project_id, sequence) — assign temp slots first so end/business updates cannot collide.
    temp_base = 10_000
    for index, phase in enumerate(phases):
        phase.sequence = temp_base + index
    db.flush()

    if start:
        start.sequence = 0
    for index, phase in enumerate(business, start=1):
        phase.sequence = index
    if end:
        end.sequence = len(business) + 1


def assert_not_system_phase(phase: GePhase) -> None:
    from fastapi import HTTPException

    if phase.is_system:
        raise HTTPException(status_code=403, detail={"detail": "system_phase_immutable"})
