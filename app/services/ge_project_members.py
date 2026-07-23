"""Project members roster (M37 · §4.2.5)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeProject, GeProjectMember, GeProjectRoleOption, GeTask
from app.services.ge_access import can_read_project, require_govern_project
from app.services.ge_accountability import display_name
from app.services.ge_graph import now_iso

SLUG_PROJECT_MANAGER = "project_manager"
SLUG_MEMBER = "member"


def _project_or_404(db: Session, project_id: str) -> GeProject:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    return project


def _role_or_404(db: Session, role_option_id: str) -> GeProjectRoleOption:
    role = db.get(GeProjectRoleOption, role_option_id)
    if role is None:
        raise HTTPException(status_code=404, detail={"detail": "role_option_not_found"})
    return role


def resolve_role_by_slug(db: Session, slug: str) -> GeProjectRoleOption:
    role = db.query(GeProjectRoleOption).filter(GeProjectRoleOption.slug == slug).first()
    if role is None:
        raise HTTPException(status_code=404, detail={"detail": "role_option_not_found"})
    return role


def _member_row(member: GeProjectMember, role: GeProjectRoleOption) -> dict[str, Any]:
    return {
        "user_id": member.user_id,
        "display_name": display_name(member.user_id),
        "role_option_id": role.id,
        "role_name": role.name,
        "role_slug": role.slug,
    }


def _sort_member_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[int, str]:
        name = str(row.get("display_name") or "").strip()
        if not name:
            return (1, "")
        return (0, name.casefold())

    return sorted(rows, key=sort_key)


def list_role_options(db: Session) -> dict[str, Any]:
    roles = db.query(GeProjectRoleOption).order_by(GeProjectRoleOption.name.asc()).all()
    return {
        "role_options": [
            {"id": r.id, "name": r.name, "slug": r.slug, "created_at": r.created_at} for r in roles
        ]
    }


def create_role_option(
    db: Session,
    body: dict[str, Any],
    *,
    user: AuthUser,
) -> dict[str, Any]:
    """JWT callers are always rejected; reviewers create via BFF service token."""
    if user.auth_method == "jwt":
        raise HTTPException(status_code=403, detail={"detail": "reviewer_required"})
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    raw_slug = body.get("slug")
    slug = str(raw_slug).strip() if raw_slug is not None else None
    if slug == "":
        slug = None
    now = now_iso()
    role = GeProjectRoleOption(id=str(uuid.uuid4()), name=name, slug=slug, created_at=now)
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"detail": "role_name_conflict"}) from exc
    db.refresh(role)
    return {"id": role.id, "name": role.name, "slug": role.slug, "created_at": role.created_at}


def list_members(db: Session, project_id: str, user: AuthUser) -> dict[str, Any]:
    project = _project_or_404(db, project_id)
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "forbidden"})
    members = db.query(GeProjectMember).filter(GeProjectMember.project_id == project_id).all()
    role_ids = {m.role_option_id for m in members}
    roles = {
        r.id: r
        for r in db.query(GeProjectRoleOption).filter(GeProjectRoleOption.id.in_(role_ids)).all()
    } if role_ids else {}
    rows = [_member_row(m, roles[m.role_option_id]) for m in members if m.role_option_id in roles]
    return {"members": _sort_member_rows(rows)}


def add_member(db: Session, project_id: str, body: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    project = _project_or_404(db, project_id)
    require_govern_project(db, project, user)
    user_id = str(body.get("user_id") or "").strip()
    role_option_id = str(body.get("role_option_id") or "").strip()
    if not user_id or not role_option_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    role = _role_or_404(db, role_option_id)
    existing = (
        db.query(GeProjectMember)
        .filter(GeProjectMember.project_id == project_id, GeProjectMember.user_id == user_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail={"detail": "member_already_exists"})
    now = now_iso()
    member = GeProjectMember(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=user_id,
        role_option_id=role.id,
        created_at=now,
        updated_at=now,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _member_row(member, role)


def patch_member(
    db: Session,
    project_id: str,
    user_id: str,
    body: dict[str, Any],
    user: AuthUser,
) -> dict[str, Any]:
    project = _project_or_404(db, project_id)
    require_govern_project(db, project, user)
    role_option_id = str(body.get("role_option_id") or "").strip()
    if not role_option_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    role = _role_or_404(db, role_option_id)
    member = (
        db.query(GeProjectMember)
        .filter(GeProjectMember.project_id == project_id, GeProjectMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail={"detail": "member_not_found"})
    member.role_option_id = role.id
    member.updated_at = now_iso()
    db.commit()
    db.refresh(member)
    return _member_row(member, role)


def delete_member(db: Session, project_id: str, user_id: str, user: AuthUser) -> None:
    project = _project_or_404(db, project_id)
    require_govern_project(db, project, user)
    if user_id == project.pm_user_id:
        raise HTTPException(status_code=409, detail={"detail": "cannot_remove_pm"})
    member = (
        db.query(GeProjectMember)
        .filter(GeProjectMember.project_id == project_id, GeProjectMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail={"detail": "member_not_found"})
    db.delete(member)
    db.commit()


def upsert_pm(db: Session, *, project_id: str, pm_user_id: str) -> None:
    """Ensure PM row exists with project_manager (force role)."""
    role = resolve_role_by_slug(db, SLUG_PROJECT_MANAGER)
    now = now_iso()
    db.flush()
    member = (
        db.query(GeProjectMember)
        .filter(GeProjectMember.project_id == project_id, GeProjectMember.user_id == pm_user_id)
        .first()
    )
    if member is None:
        db.add(
            GeProjectMember(
                id=str(uuid.uuid4()),
                project_id=project_id,
                user_id=pm_user_id,
                role_option_id=role.id,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        member.role_option_id = role.id
        member.updated_at = now
    db.flush()


def replace_pm_on_change(
    db: Session,
    *,
    project_id: str,
    old_pm_user_id: str,
    new_pm_user_id: str,
) -> None:
    if old_pm_user_id == new_pm_user_id:
        upsert_pm(db, project_id=project_id, pm_user_id=new_pm_user_id)
        return
    db.flush()
    old = (
        db.query(GeProjectMember)
        .filter(GeProjectMember.project_id == project_id, GeProjectMember.user_id == old_pm_user_id)
        .first()
    )
    if old is not None:
        db.delete(old)
        db.flush()
    upsert_pm(db, project_id=project_id, pm_user_id=new_pm_user_id)


def ensure_member_for_assignee(db: Session, *, project_id: str, assignee_user_id: str) -> None:
    """If assignee has no roster row, insert as member; existing role unchanged."""
    assignee = str(assignee_user_id or "").strip()
    if not assignee:
        return
    db.flush()
    existing = (
        db.query(GeProjectMember)
        .filter(GeProjectMember.project_id == project_id, GeProjectMember.user_id == assignee)
        .first()
    )
    if existing is not None:
        return
    role = resolve_role_by_slug(db, SLUG_MEMBER)
    now = now_iso()
    db.add(
        GeProjectMember(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=assignee,
            role_option_id=role.id,
            created_at=now,
            updated_at=now,
        )
    )
    db.flush()


def ensure_members_for_project_assignees(db: Session, *, project_id: str) -> None:
    assignees = {
        t.assignee_user_id
        for t in db.query(GeTask).filter(GeTask.project_id == project_id).all()
        if t.assignee_user_id
    }
    for uid in sorted(assignees):
        ensure_member_for_assignee(db, project_id=project_id, assignee_user_id=uid)
