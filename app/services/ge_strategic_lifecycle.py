"""Read-time strategic lifecycle refresh (M29 · §3.3.8.2 · no cron).

GE-PERF.1: process-local TTL (≤60s) skips full-table batch; writers call
``invalidate_lifecycle_refresh`` (spec §3.1.1).
"""

from __future__ import annotations

import time
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

# Spec C2 / §3.1 — process-local TTL ≤60s
LIFECYCLE_BATCH_TTL_SECONDS = 60.0

_last_lifecycle_batch_monotonic: float | None = None


def invalidate_lifecycle_refresh() -> None:
    """Force the next ``refresh_lifecycle_batch`` (or entity batch) to run."""
    global _last_lifecycle_batch_monotonic
    _last_lifecycle_batch_monotonic = None


def _lifecycle_batch_due() -> bool:
    if _last_lifecycle_batch_monotonic is None:
        return True
    return (time.monotonic() - _last_lifecycle_batch_monotonic) >= LIFECYCLE_BATCH_TTL_SECONDS


def _mark_lifecycle_batch_done() -> None:
    global _last_lifecycle_batch_monotonic
    _last_lifecycle_batch_monotonic = time.monotonic()


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


def refresh_lifecycle_entities(
    db: Session,
    objectives: list[GeObjective],
    programs: list[GeProgram],
) -> None:
    """Apply batch refresh to preloaded rows; respects TTL (no extra SELECTs).

    Does not ``flush`` — callers that already hold the rows must avoid
    expire-on-flush reloads during in-memory tree assembly; ``db.commit()``
    at the end of the request persists changes.
    """
    if not _lifecycle_batch_due():
        return
    for obj in objectives:
        _apply_refresh_with_db(db, obj, entity_type="objective")
    for prog in programs:
        _apply_refresh_with_db(db, prog, entity_type="program")
    _mark_lifecycle_batch_done()


def refresh_lifecycle_batch(db: Session) -> None:
    if not _lifecycle_batch_due():
        return
    for obj in db.query(GeObjective).filter(GeObjective.is_default.is_(False)).all():
        _apply_refresh_with_db(db, obj, entity_type="objective")
    for prog in db.query(GeProgram).filter(GeProgram.is_default.is_(False)).all():
        _apply_refresh_with_db(db, prog, entity_type="program")
    _mark_lifecycle_batch_done()
    db.flush()
