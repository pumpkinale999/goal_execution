"""K27.6 · batch project access table for BFF X-KB-Project-Access."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeProject, GeProjectMember, GeProjectRoleOption
from app.services.ge_access import filter_projects_for_user
from app.services.ge_project_members import SINGLETON_ROLE_SLUGS
from app.services.ge_goal_subtree_governor import is_goal_subtree_governor

_EMPTY_SINGLETONS = {slug: "" for slug in sorted(SINGLETON_ROLE_SLUGS)}


def _role_for_user(db: Session, project: GeProject, user_id: str) -> str:
    if str(project.pm_user_id or "").strip() == user_id:
        return "pm"
    if is_goal_subtree_governor(db, user_id=user_id, project_id=project.id):
        return "governor"
    return "member"


def _singletons_by_project(
    db: Session,
    project_ids: list[str],
) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {
        pid: dict(_EMPTY_SINGLETONS) for pid in project_ids
    }
    if not project_ids:
        return out
    slug_roles = {
        r.id: r.slug
        for r in db.query(GeProjectRoleOption)
        .filter(GeProjectRoleOption.slug.in_(tuple(SINGLETON_ROLE_SLUGS)))
        .all()
    }
    if not slug_roles:
        return out
    members = (
        db.query(GeProjectMember)
        .filter(
            GeProjectMember.project_id.in_(project_ids),
            GeProjectMember.role_option_id.in_(tuple(slug_roles.keys())),
        )
        .all()
    )
    for row in members:
        slug = slug_roles.get(row.role_option_id)
        if not slug or slug not in SINGLETON_ROLE_SLUGS:
            continue
        pid = row.project_id
        if pid not in out:
            continue
        # First holder wins (singleton demotion keeps one)
        if not out[pid].get(slug):
            out[pid][slug] = str(row.user_id or "").strip()
    return out


def build_project_access_for_user(
    db: Session,
    user: AuthUser,
    *,
    force_member_all: bool = False,
) -> dict[str, Any]:
    """Return ``{projects: [{project_id, role, doc_singletons}]}``.

    ``force_member_all`` (service/reviewer BFF): every non-deleted project with
    ``role=member`` (matches current skstudio reviewer header behavior).
    """
    projects = (
        db.query(GeProject)
        .filter(GeProject.deleted_at.is_(None))
        .order_by(GeProject.program_id, GeProject.sort_order, GeProject.name)
        .all()
    )
    if force_member_all:
        visible = [p for p in projects if p.deleted_at is None]
    else:
        visible = filter_projects_for_user(db, projects, user)

    pids = [p.id for p in visible]
    singles = _singletons_by_project(db, pids)
    uid = str(user.user_id).strip()
    rows: list[dict[str, Any]] = []
    for project in visible:
        if force_member_all:
            role = "member"
        else:
            role = _role_for_user(db, project, uid)
        rows.append(
            {
                "project_id": project.id,
                "role": role,
                "doc_singletons": singles.get(project.id, dict(_EMPTY_SINGLETONS)),
            }
        )
    return {"projects": rows}
