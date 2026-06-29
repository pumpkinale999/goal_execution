"""Read-time strategic lifecycle refresh (M29 · §3.3.8.2 · no cron)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.ge import GeObjective, GeProgram
from app.services.ge_graph import now_iso, record_audit
from app.services.ge_strategic_period import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_ARCHIVED,
    LIFECYCLE_PENDING,
    parse_ymd,
    today,
)


def _should_skip(entity: GeObjective | GeProgram) -> bool:
    return bool(entity.is_default)


def _apply_refresh_with_db(db: Session, entity: GeObjective | GeProgram, *, entity_type: str) -> bool:
    if _should_skip(entity):
        return False
    if not entity.period_end:
        return False
    current = entity.lifecycle_status or LIFECYCLE_ACTIVE
    end = parse_ymd(entity.period_end)
    now = today()
    changed = False

    if current == LIFECYCLE_ACTIVE and now > end:
        entity.lifecycle_status = LIFECYCLE_PENDING
        entity.updated_at = now_iso()
        record_audit(
            db,
            actor_user_id="system",
            entity_type=entity_type,
            entity_id=entity.id,
            action="lifecycle_auto_pending",
            payload={"from": LIFECYCLE_ACTIVE, "to": LIFECYCLE_PENDING},
        )
        changed = True
        current = LIFECYCLE_PENDING

    if current == LIFECYCLE_PENDING and now > end + timedelta(days=30):
        entity.lifecycle_status = LIFECYCLE_ARCHIVED
        entity.updated_at = now_iso()
        record_audit(
            db,
            actor_user_id="system",
            entity_type=entity_type,
            entity_id=entity.id,
            action="lifecycle_auto_not_met",
            payload={"from": LIFECYCLE_PENDING, "to": LIFECYCLE_ARCHIVED},
        )
        changed = True

    return changed


def refresh_lifecycle_on_read(db: Session, entity: GeObjective | GeProgram) -> None:
    entity_type = "objective" if isinstance(entity, GeObjective) else "program"
    _apply_refresh_with_db(db, entity, entity_type=entity_type)


def refresh_lifecycle_batch(db: Session) -> None:
    for obj in db.query(GeObjective).filter(GeObjective.is_default == 0).all():
        _apply_refresh_with_db(db, obj, entity_type="objective")
    for prog in db.query(GeProgram).filter(GeProgram.is_default == 0).all():
        _apply_refresh_with_db(db, prog, entity_type="program")
    db.flush()
