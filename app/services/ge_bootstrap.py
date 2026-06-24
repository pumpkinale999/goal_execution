"""Bootstrap default objective/program (§7)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.constants import (
    DEFAULT_OBJECTIVE_NAME,
    DEFAULT_PROGRAM_NAME,
    DEFAULT_SUB_OBJECTIVE_NAME,
    GE_DEFAULT_OBJECTIVE_ID,
    GE_DEFAULT_PROGRAM_ID,
    GE_DEFAULT_SUB_OBJECTIVE_ID,
)
from app.models.ge import GeObjective, GeProgram


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_ge_bootstrap(db: Session) -> None:
    now = _now_iso()
    objective = db.get(GeObjective, GE_DEFAULT_OBJECTIVE_ID)
    if objective is None:
        db.add(
            GeObjective(
                id=GE_DEFAULT_OBJECTIVE_ID,
                name=DEFAULT_OBJECTIVE_NAME,
                level="company",
                parent_id=None,
                owner_user_id=None,
                is_default=True,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()

    sub_objective = db.get(GeObjective, GE_DEFAULT_SUB_OBJECTIVE_ID)
    if sub_objective is None:
        db.add(
            GeObjective(
                id=GE_DEFAULT_SUB_OBJECTIVE_ID,
                name=DEFAULT_SUB_OBJECTIVE_NAME,
                level="sub",
                parent_id=GE_DEFAULT_OBJECTIVE_ID,
                owner_user_id=None,
                is_default=True,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()

    program = db.get(GeProgram, GE_DEFAULT_PROGRAM_ID)
    if program is None:
        db.add(
            GeProgram(
                id=GE_DEFAULT_PROGRAM_ID,
                name=DEFAULT_PROGRAM_NAME,
                objective_id=GE_DEFAULT_SUB_OBJECTIVE_ID,
                owner_user_id=None,
                is_default=True,
                created_at=now,
                updated_at=now,
            )
        )
    elif program.objective_id != GE_DEFAULT_SUB_OBJECTIVE_ID:
        program.objective_id = GE_DEFAULT_SUB_OBJECTIVE_ID
        program.updated_at = now

    stale_programs = (
        db.query(GeProgram)
        .filter(GeProgram.objective_id == GE_DEFAULT_OBJECTIVE_ID)
        .all()
    )
    for stale in stale_programs:
        stale.objective_id = GE_DEFAULT_SUB_OBJECTIVE_ID
        stale.updated_at = now

    db.commit()


def default_program_id(db: Session) -> str:
    ensure_ge_bootstrap(db)
    return GE_DEFAULT_PROGRAM_ID
