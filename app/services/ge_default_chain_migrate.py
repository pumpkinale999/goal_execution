"""Migrate business content off the global default chain (b1/b3/b2)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.constants import (
    DEFAULT_OBJECTIVE_NAME,
    DEFAULT_SUB_OBJECTIVE_NAME,
    GE_DEFAULT_OBJECTIVE_ID,
    GE_DEFAULT_SUB_OBJECTIVE_ID,
)
from app.models.ge import GeObjective, GeProgram
from app.services.ge_bootstrap import ensure_ge_bootstrap
from app.services.ge_graph import now_iso, record_audit
from app.services.ge_strategic_period import LIFECYCLE_ACTIVE, planning_year_from_start, year_bounds


def _active_annual_for_year(db: Session, year: int) -> GeObjective | None:
    start, _ = year_bounds(year)
    return (
        db.query(GeObjective)
        .filter(
            GeObjective.level == "company",
            GeObjective.is_default == 0,
            GeObjective.lifecycle_status == LIFECYCLE_ACTIVE,
            GeObjective.period_start == start,
        )
        .first()
    )


def default_chain_has_movable_content(db: Session, b1: GeObjective, b3: GeObjective) -> bool:
    if b1.name != DEFAULT_OBJECTIVE_NAME:
        return True
    if b1.owner_user_id:
        return True
    if b1.primary_department_id:
        return True
    if b3.name != DEFAULT_SUB_OBJECTIVE_NAME:
        return True
    if b3.owner_user_id:
        return True
    if db.query(GeObjective).filter(GeObjective.parent_id == b1.id, GeObjective.is_default == 0).count():
        return True
    if db.query(GeProgram).filter(GeProgram.objective_id == b3.id, GeProgram.is_default == 0).count():
        return True
    return False


def move_default_chain_content(
    db: Session,
    target_company: GeObjective,
    *,
    b1: GeObjective,
    b3: GeObjective,
    now: str,
) -> None:
    moved_subs: list[GeObjective] = []
    for sub in db.query(GeObjective).filter(GeObjective.parent_id == b1.id, GeObjective.is_default == 0).all():
        sub.parent_id = target_company.id
        sub.updated_at = now
        moved_subs.append(sub)

    orphan_programs = (
        db.query(GeProgram).filter(GeProgram.objective_id == b3.id, GeProgram.is_default == 0).all()
    )
    if not orphan_programs:
        return

    if moved_subs:
        target_sub = moved_subs[0]
    else:
        start, end = year_bounds(planning_year_from_start(target_company.period_start) or 2000)
        target_sub = GeObjective(
            id=str(uuid.uuid4()),
            name=b3.name if b3.name != DEFAULT_SUB_OBJECTIVE_NAME else DEFAULT_SUB_OBJECTIVE_NAME,
            level="sub",
            parent_id=target_company.id,
            owner_user_id=b3.owner_user_id or b1.owner_user_id or target_company.owner_user_id,
            is_default=0,
            period_granularity=b3.period_granularity or "year",
            period_start=b3.period_start or start,
            period_end=b3.period_end or end,
            lifecycle_status=LIFECYCLE_ACTIVE,
            primary_department_id=b3.primary_department_id,
            primary_department_needs_confirmation=b3.primary_department_needs_confirmation or 0,
            created_at=now,
            updated_at=now,
        )
        db.add(target_sub)
        db.flush()
    for prog in orphan_programs:
        prog.objective_id = target_sub.id
        prog.updated_at = now


def reset_default_chain_placeholders(
    db: Session,
    *,
    b1: GeObjective,
    b3: GeObjective,
    start: str,
    end: str,
    now: str,
) -> None:
    b1.name = DEFAULT_OBJECTIVE_NAME
    b1.owner_user_id = None
    b1.period_granularity = "year"
    b1.period_start = start
    b1.period_end = end
    b1.primary_department_id = None
    b1.primary_department_needs_confirmation = 0
    b1.updated_at = now
    b3.name = DEFAULT_SUB_OBJECTIVE_NAME
    b3.updated_at = now


def migrate_default_chain_off_placeholder(
    db: Session, *, actor_user_id: str = "system"
) -> dict[str, Any] | None:
    """Move default-chain business content onto a formal annual root; reset placeholders."""
    ensure_ge_bootstrap(db)
    b1 = db.get(GeObjective, GE_DEFAULT_OBJECTIVE_ID)
    b3 = db.get(GeObjective, GE_DEFAULT_SUB_OBJECTIVE_ID)
    if b1 is None or b3 is None:
        return None
    if not default_chain_has_movable_content(db, b1, b3):
        return None

    year = planning_year_from_start(b1.period_start)
    if year is None:
        from datetime import UTC, datetime

        year = datetime.now(UTC).year
    start, end = year_bounds(year)
    now = now_iso()
    annual = _active_annual_for_year(db, year)

    if annual is None:
        annual_name = b1.name if b1.name != DEFAULT_OBJECTIVE_NAME else f"{year} 年度战略目标"
        annual = GeObjective(
            id=str(uuid.uuid4()),
            name=annual_name,
            level="company",
            parent_id=None,
            owner_user_id=b1.owner_user_id,
            is_default=0,
            period_granularity="year",
            period_start=start,
            period_end=end,
            lifecycle_status=LIFECYCLE_ACTIVE,
            primary_department_id=b1.primary_department_id,
            primary_department_needs_confirmation=b1.primary_department_needs_confirmation or 0,
            created_at=now,
            updated_at=now,
        )
        db.add(annual)
        db.flush()
        action = "promote_default_chain_to_annual"
    else:
        action = "migrate_default_chain_to_existing_annual"

    move_default_chain_content(db, annual, b1=b1, b3=b3, now=now)
    reset_default_chain_placeholders(db, b1=b1, b3=b3, start=start, end=end, now=now)
    record_audit(
        db,
        actor_user_id=actor_user_id,
        entity_type="objective",
        entity_id=annual.id,
        action=action,
        payload={"planning_year": year, "source_objective_id": GE_DEFAULT_OBJECTIVE_ID},
    )
    db.flush()
    from app.services.ge_strategic import objective_out

    return objective_out(annual)


def run_default_chain_migration_backfill(connection, *, dry_run: bool = False) -> dict[str, int]:
    from sqlalchemy.orm import Session

    session = Session(bind=connection)
    try:
        result = migrate_default_chain_off_placeholder(session, actor_user_id="system")
        stats = {"migrated": 1 if result else 0}
        if dry_run:
            session.rollback()
        return stats
    finally:
        session.close()
