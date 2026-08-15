"""PA goal list roles batch (G-PERF-M1) — my_roles[] + roster_role, set precompute."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeProject, GeProjectMember, GeProjectRoleOption, GeTask
from app.services.ge_access import (
    _governed_program_ids_for_user,
    filter_projects_for_user,
)


def _normalize_match_ids(user: AuthUser, match_user_ids: set[str] | None) -> set[str]:
    out = {str(user.user_id).strip()}
    for raw in match_user_ids or set():
        uid = str(raw or "").strip()
        if uid:
            out.add(uid)
    return {x for x in out if x}


def _governed_programs_for_ids(db: Session, match_ids: set[str]) -> set[str]:
    governed: set[str] = set()
    for uid in match_ids:
        governed |= _governed_program_ids_for_user(db, uid)
    return governed


def _participant_project_ids_for_ids(
    db: Session, match_ids: set[str], project_ids: list[str]
) -> set[str]:
    if not match_ids or not project_ids:
        return set()
    member_rows = (
        db.query(GeProjectMember.project_id)
        .filter(
            GeProjectMember.user_id.in_(tuple(match_ids)),
            GeProjectMember.project_id.in_(project_ids),
        )
        .all()
    )
    assignee_rows = (
        db.query(GeTask.project_id)
        .filter(
            GeTask.assignee_user_id.in_(tuple(match_ids)),
            GeTask.project_id.in_(project_ids),
        )
        .distinct()
        .all()
    )
    return {row[0] for row in member_rows} | {row[0] for row in assignee_rows}


def _roster_slug_by_project(
    db: Session, match_ids: set[str], project_ids: list[str]
) -> dict[str, str]:
    """First roster role_slug per project for any match_user_id."""
    if not match_ids or not project_ids:
        return {}
    rows = (
        db.query(GeProjectMember.project_id, GeProjectRoleOption.slug)
        .join(
            GeProjectRoleOption,
            GeProjectRoleOption.id == GeProjectMember.role_option_id,
        )
        .filter(
            GeProjectMember.user_id.in_(tuple(match_ids)),
            GeProjectMember.project_id.in_(project_ids),
        )
        .all()
    )
    out: dict[str, str] = {}
    for project_id, slug in rows:
        if project_id not in out and slug:
            out[project_id] = str(slug)
    return out


def build_pa_project_roles_for_user(
    db: Session,
    user: AuthUser,
    *,
    match_user_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Return ``{projects: [{project_id, my_roles, roster_role}]}`` for PA list enrich.

    Visibility ≡ ``filter_projects_for_user`` (reviewer → all non-deleted).
    Role decoration uses ``match_user_ids ∪ {user.user_id}`` in one set-precompute pass;
    does **not** call ``is_goal_subtree_governor`` per project.
    """
    match_ids = _normalize_match_ids(user, match_user_ids)
    projects = (
        db.query(GeProject)
        .filter(GeProject.deleted_at.is_(None))
        .order_by(GeProject.program_id, GeProject.sort_order, GeProject.name)
        .all()
    )
    visible = filter_projects_for_user(db, projects, user)
    pids = [p.id for p in visible]
    participant_ids = _participant_project_ids_for_ids(db, match_ids, pids)
    governed_programs = _governed_programs_for_ids(db, match_ids)
    roster_by_pid = _roster_slug_by_project(db, match_ids, pids)

    rows: list[dict[str, Any]] = []
    for project in visible:
        roles: list[str] = []
        pm = str(project.pm_user_id or "").strip()
        if pm and pm in match_ids:
            roles.append("pm")
        if project.id in participant_ids:
            if "participant" not in roles:
                roles.append("participant")
        if project.program_id and project.program_id in governed_programs:
            if "steward" not in roles:
                roles.append("steward")
        roster_role = roster_by_pid.get(project.id)
        if roster_role and "participant" not in roles:
            roles.append("participant")
        rows.append(
            {
                "project_id": project.id,
                "my_roles": roles,
                "roster_role": roster_role if roster_role else None,
            }
        )
    return {"projects": rows}
