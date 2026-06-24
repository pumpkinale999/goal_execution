"""Phase progress notifications (§4.4.1)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ge import GeExecutionNotification
from app.services.ge_graph import now_iso


def upsert_phase_notifications(db: Session, event: dict[str, Any], participant_ids: set[str]) -> None:
    kind = "ge_phase_progress"
    now = now_iso()
    for user_id in participant_ids:
        phase_id = event.get("phase_id")
        project_id = event["project_id"]
        existing = (
            db.query(GeExecutionNotification)
            .filter(
                GeExecutionNotification.user_id == user_id,
                GeExecutionNotification.project_id == project_id,
                GeExecutionNotification.phase_id == phase_id,
                GeExecutionNotification.kind == kind,
                GeExecutionNotification.read_at.is_(None),
            )
            .first()
        )
        title = f"阶段已开启：{event.get('phase_name')}"
        if event.get("event") == "ge.gate.opened":
            title = f"门已打开：{event.get('phase_name')}"
        payload = json.dumps(
            {
                "event": event.get("event"),
                "phase_name": event.get("phase_name"),
                "sequence": event.get("sequence"),
            }
        )
        if existing:
            existing.payload = payload
            existing.gate_id = event.get("gate_id")
            existing.created_at = now
        else:
            db.add(
                GeExecutionNotification(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    kind=kind,
                    project_id=project_id,
                    phase_id=phase_id,
                    gate_id=event.get("gate_id"),
                    payload=payload,
                    read_at=None,
                    created_at=now,
                )
            )


def list_notifications(db: Session, user_id: str, *, unread_only: bool = False) -> list[dict]:
    q = db.query(GeExecutionNotification).filter(GeExecutionNotification.user_id == user_id)
    if unread_only:
        q = q.filter(GeExecutionNotification.read_at.is_(None))
    rows = q.order_by(GeExecutionNotification.created_at.desc()).all()
    result = []
    for row in rows:
        payload = json.loads(row.payload or "{}")
        title = f"阶段已开启：{payload.get('phase_name', '')}"
        if payload.get("event") == "ge.gate.opened":
            title = f"门已打开：{payload.get('phase_name', '')}"
        result.append(
            {
                "id": row.id,
                "kind": row.kind,
                "project_id": row.project_id,
                "phase_id": row.phase_id,
                "gate_id": row.gate_id,
                "title": title,
                "read_at": row.read_at,
                "created_at": row.created_at,
            }
        )
    return result


def mark_notification_read(db: Session, user_id: str, notification_id: str) -> dict[str, Any]:
    row = (
        db.query(GeExecutionNotification)
        .filter(
            GeExecutionNotification.id == notification_id,
            GeExecutionNotification.user_id == user_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if row.read_at is None:
        row.read_at = now_iso()
    db.commit()
    return {"id": row.id, "read_at": row.read_at}


def mark_all_notifications_read(db: Session, user_id: str) -> dict[str, int]:
    now = now_iso()
    rows = (
        db.query(GeExecutionNotification)
        .filter(
            GeExecutionNotification.user_id == user_id,
            GeExecutionNotification.read_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.read_at = now
    db.commit()
    return {"updated": len(rows)}
