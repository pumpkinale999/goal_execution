"""K29: per-note write grants for project members."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeProject, GeProjectMember, GeProjectNoteWriteGrant
from app.services.ge_access import can_read_project, require_govern_project
from app.services.ge_graph import now_iso


def _project_or_404(db: Session, project_id: str) -> GeProject:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    return project


def delete_grants_for_user(db: Session, *, project_id: str, user_id: str) -> None:
    """Remove all note write grants for a user on a project (W6). Caller commits."""
    db.query(GeProjectNoteWriteGrant).filter(
        GeProjectNoteWriteGrant.project_id == project_id,
        GeProjectNoteWriteGrant.user_id == user_id,
    ).delete(synchronize_session=False)


def delete_grants_for_project(db: Session, *, project_id: str) -> None:
    """Remove all note write grants for a project (W16). Caller commits."""
    db.query(GeProjectNoteWriteGrant).filter(
        GeProjectNoteWriteGrant.project_id == project_id,
    ).delete(synchronize_session=False)


def list_write_grants(
    db: Session,
    project_id: str,
    note_id: str,
    user: AuthUser,
) -> dict[str, Any]:
    project = _project_or_404(db, project_id)
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "forbidden"})
    nid = str(note_id or "").strip()
    if not nid:
        raise HTTPException(status_code=400, detail={"detail": "invalid_note_id"})

    member_ids = {
        m.user_id
        for m in db.query(GeProjectMember).filter(GeProjectMember.project_id == project_id).all()
    }
    rows = (
        db.query(GeProjectNoteWriteGrant)
        .filter(
            GeProjectNoteWriteGrant.project_id == project_id,
            GeProjectNoteWriteGrant.note_id == nid,
        )
        .all()
    )
    # ∩ current members (stale rows must not surface)
    user_ids = sorted({r.user_id for r in rows if r.user_id in member_ids})
    return {"note_id": nid, "user_ids": user_ids}


def replace_write_grants(
    db: Session,
    project_id: str,
    note_id: str,
    body: dict[str, Any],
    user: AuthUser,
) -> dict[str, Any]:
    project = _project_or_404(db, project_id)
    require_govern_project(db, project, user)
    nid = str(note_id or "").strip()
    if not nid:
        raise HTTPException(status_code=400, detail={"detail": "invalid_note_id"})

    raw_ids = body.get("user_ids")
    if not isinstance(raw_ids, list):
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})

    member_ids = {
        m.user_id
        for m in db.query(GeProjectMember).filter(GeProjectMember.project_id == project_id).all()
    }
    # Governance roles are not stored; silently drop PM (and any non-members → 400)
    wanted: set[str] = set()
    for item in raw_ids:
        uid = str(item or "").strip()
        if not uid:
            continue
        if uid == project.pm_user_id:
            continue  # PN-NW-06: silent ignore PM
        if uid not in member_ids:
            raise HTTPException(status_code=400, detail={"detail": "not_project_member", "user_id": uid})
        wanted.add(uid)

    db.query(GeProjectNoteWriteGrant).filter(
        GeProjectNoteWriteGrant.project_id == project_id,
        GeProjectNoteWriteGrant.note_id == nid,
    ).delete(synchronize_session=False)

    now = now_iso()
    for uid in sorted(wanted):
        db.add(
            GeProjectNoteWriteGrant(
                id=str(uuid.uuid4()),
                project_id=project_id,
                note_id=nid,
                user_id=uid,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()
    return {"note_id": nid, "user_ids": sorted(wanted)}


def user_has_note_write_grant(
    db: Session,
    *,
    project_id: str,
    note_id: str,
    user_id: str,
) -> bool:
    """True if explicit grant exists and user is still a member."""
    uid = str(user_id or "").strip()
    nid = str(note_id or "").strip()
    if not uid or not nid:
        return False
    member = (
        db.query(GeProjectMember)
        .filter(GeProjectMember.project_id == project_id, GeProjectMember.user_id == uid)
        .first()
    )
    if member is None:
        return False
    row = (
        db.query(GeProjectNoteWriteGrant)
        .filter(
            GeProjectNoteWriteGrant.project_id == project_id,
            GeProjectNoteWriteGrant.note_id == nid,
            GeProjectNoteWriteGrant.user_id == uid,
        )
        .first()
    )
    return row is not None
