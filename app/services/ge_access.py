"""Project access control (§4.0 · §4.2.1 · M21 governance)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeProject, GeTask


def project_participant_user_ids(db: Session, project: GeProject) -> set[str]:
    ids = {project.pm_user_id}
    for task in db.query(GeTask).filter(GeTask.project_id == project.id).all():
        if task.assignee_user_id:
            ids.add(task.assignee_user_id)
    return ids


def is_participant(db: Session, project: GeProject, user_id: str) -> bool:
    return user_id in project_participant_user_ids(db, project)


def can_read_project(db: Session, project: GeProject, user: AuthUser) -> bool:
    if project.deleted_at is not None:
        return False
    if user.auth_method == "service":
        return True
    if is_participant(db, project, user.user_id):
        return True
    return project.created_by_user_id == user.user_id


def filter_projects_for_user(db: Session, projects: list[GeProject], user: AuthUser) -> list[GeProject]:
    if user.auth_method == "service":
        return [p for p in projects if p.deleted_at is None]
    return [p for p in projects if can_read_project(db, p, user)]


def can_govern_project(project: GeProject, user: AuthUser) -> bool:
    """PM (JWT) or reviewer governance (service token · BFF verified)."""
    if project.deleted_at is not None:
        return False
    if user.auth_method == "service":
        return True
    if user.auth_method == "jwt" and user.user_id == project.pm_user_id:
        return True
    return False


def require_govern_project(project: GeProject, user: AuthUser) -> None:
    if not can_govern_project(project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_governor"})
