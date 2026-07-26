"""Project access control (§4.0 · §4.2.1 · M21 governance · M24 subtree steward).

GE-PERF.2: ``filter_projects_for_user`` uses set precompute — no per-project
``is_subtree_governor`` in the list loop.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeObjective, GeProgram, GeProject, GeProjectMember, GeTask
from app.services.ge_subtree_governor import is_subtree_governor


def project_participant_user_ids(db: Session, project: GeProject) -> set[str]:
    ids = {project.pm_user_id}
    for task in db.query(GeTask).filter(GeTask.project_id == project.id).all():
        if task.assignee_user_id:
            ids.add(task.assignee_user_id)
    for member in db.query(GeProjectMember).filter(GeProjectMember.project_id == project.id).all():
        ids.add(member.user_id)
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
    if project.created_by_user_id == user.user_id:
        return True
    if user.auth_method == "jwt":
        return is_subtree_governor(db, user_id=user.user_id, project_id=project.id)
    return False


def _governed_program_ids_for_user(db: Session, user_id: str) -> set[str]:
    """Programs the user governs via program ownership or objective ancestor ownership."""
    uid = str(user_id).strip()
    if not uid:
        return set()

    objectives = db.query(GeObjective.id, GeObjective.parent_id, GeObjective.owner_user_id).all()
    children_by_parent: dict[str | None, list[str]] = {}
    owned: set[str] = set()
    for obj_id, parent_id, owner in objectives:
        children_by_parent.setdefault(parent_id, []).append(obj_id)
        if owner and str(owner).strip() == uid:
            owned.add(obj_id)

    governed_obj_ids = set(owned)
    queue = list(owned)
    while queue:
        current = queue.pop()
        for child_id in children_by_parent.get(current, []):
            if child_id not in governed_obj_ids:
                governed_obj_ids.add(child_id)
                queue.append(child_id)

    programs = db.query(GeProgram.id, GeProgram.objective_id, GeProgram.owner_user_id).all()
    governed_programs: set[str] = set()
    for prog_id, objective_id, owner in programs:
        if owner and str(owner).strip() == uid:
            governed_programs.add(prog_id)
        elif objective_id in governed_obj_ids:
            governed_programs.add(prog_id)
    return governed_programs


def _participant_project_ids(db: Session, user_id: str, project_ids: list[str]) -> set[str]:
    if not project_ids:
        return set()
    uid = str(user_id).strip()
    member_rows = (
        db.query(GeProjectMember.project_id)
        .filter(GeProjectMember.user_id == uid, GeProjectMember.project_id.in_(project_ids))
        .all()
    )
    assignee_rows = (
        db.query(GeTask.project_id)
        .filter(GeTask.assignee_user_id == uid, GeTask.project_id.in_(project_ids))
        .distinct()
        .all()
    )
    return {row[0] for row in member_rows} | {row[0] for row in assignee_rows}


def filter_projects_for_user(db: Session, projects: list[GeProject], user: AuthUser) -> list[GeProject]:
    if user.auth_method == "service":
        return [p for p in projects if p.deleted_at is None]

    active = [p for p in projects if p.deleted_at is None]
    if not active:
        return []

    uid = user.user_id
    project_ids = [p.id for p in active]
    participant_ids = _participant_project_ids(db, uid, project_ids)
    governed_programs = (
        _governed_program_ids_for_user(db, uid) if user.auth_method == "jwt" else set()
    )

    visible: list[GeProject] = []
    for project in active:
        if project.pm_user_id == uid:
            visible.append(project)
            continue
        if project.created_by_user_id == uid:
            visible.append(project)
            continue
        if project.id in participant_ids:
            visible.append(project)
            continue
        if project.program_id in governed_programs:
            visible.append(project)
            continue
    return visible


def can_govern_project(db: Session, project: GeProject, user: AuthUser) -> bool:
    """Structure + execution governance: PM, subtree_governor (M24), or reviewer (service)."""
    if project.deleted_at is not None:
        return False
    if user.auth_method == "service":
        return True
    if user.auth_method == "jwt":
        if user.user_id == project.pm_user_id:
            return True
        return is_subtree_governor(db, user_id=user.user_id, project_id=project.id)
    return False


def can_govern_structure(db: Session, project: GeProject, user: AuthUser) -> bool:
    """Alias for can_govern_project (M24 · GE-29 · no dual-track)."""
    return can_govern_project(db, project, user)


def can_force_delete_project(db: Session, project: GeProject, user: AuthUser) -> bool:
    """Subtree owner or reviewer may soft-delete non-empty projects (UI must confirm)."""
    if project.deleted_at is not None:
        return False
    if user.auth_method == "service":
        return True
    if user.auth_method == "jwt":
        return is_subtree_governor(db, user_id=user.user_id, project_id=project.id)
    return False


def require_govern_project(db: Session, project: GeProject, user: AuthUser) -> None:
    if not can_govern_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_governor"})


def require_govern_structure(db: Session, project: GeProject, user: AuthUser) -> None:
    require_govern_project(db, project, user)


def list_governed_project_ids(db: Session, user_id: str, *, auth_method: str = "jwt") -> list[str]:
    q = db.query(GeProject).filter(GeProject.deleted_at.is_(None), GeProject.status == "active")
    if auth_method == "service":
        return [p.id for p in q.all()]
    projects = q.all()
    governed_programs = _governed_program_ids_for_user(db, user_id)
    ids: set[str] = set()
    for project in projects:
        if project.pm_user_id == user_id or project.program_id in governed_programs:
            ids.add(project.id)
    return list(ids)
