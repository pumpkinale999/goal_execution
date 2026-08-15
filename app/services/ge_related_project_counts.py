"""Per-user project counts for goal-tree program badges.

- **related** (参与): PM ∪ project members; exclude cancelled/archived/deleted.
  Not ACL visibility (reviewer/governor bulk see-all).
- **visible** (可见): ``filter_projects_for_user`` ∩ same lifecycle exclusion set.
  Invariant: for each program, related ≤ visible.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeProject, GeProjectMember
from app.services.ge_access import filter_projects_for_user

_EXCLUDED_STATUSES = frozenset({"cancelled", "archived"})


def my_related_project_counts_by_program(db: Session, user_id: str) -> dict[str, int]:
    """Return program_id → count of projects related to user (PM or member)."""
    uid = str(user_id or "").strip()
    if not uid:
        return {}

    base = (
        db.query(GeProject.program_id, GeProject.id)
        .filter(
            GeProject.deleted_at.is_(None),
            ~GeProject.status.in_(_EXCLUDED_STATUSES),
        )
    )
    pm_rows = base.filter(GeProject.pm_user_id == uid).all()
    member_rows = (
        base.join(GeProjectMember, GeProjectMember.project_id == GeProject.id)
        .filter(GeProjectMember.user_id == uid)
        .all()
    )

    by_program: dict[str, set[str]] = {}
    for program_id, project_id in (*pm_rows, *member_rows):
        by_program.setdefault(program_id, set()).add(project_id)
    return {program_id: len(ids) for program_id, ids in by_program.items()}


def my_visible_project_counts_by_program(db: Session, user: AuthUser) -> dict[str, int]:
    """Return program_id → count of ACL-visible effective projects for user.

    Effective = not deleted and not cancelled/archived. Uses one-shot
    ``filter_projects_for_user`` (no per-program can_read loops).
    """
    projects = (
        db.query(GeProject)
        .filter(
            GeProject.deleted_at.is_(None),
            ~GeProject.status.in_(_EXCLUDED_STATUSES),
        )
        .all()
    )
    visible = filter_projects_for_user(db, projects, user)
    by_program: dict[str, int] = {}
    for project in visible:
        pid = project.program_id
        if not pid:
            continue
        by_program[pid] = by_program.get(pid, 0) + 1
    return by_program
