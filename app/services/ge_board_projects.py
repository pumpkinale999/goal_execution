"""Objective board-projects read API (PRA §4.11 sub · §4.12 company).

GE-VIS-1: objective must be in personal_tree; programs[] trimmed to projection.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_access import filter_projects_for_user
from app.services.ge_personal_tree import (
    compute_personal_tree_sets,
    objective_in_projection,
)
from app.services.ge_sort_order import sibling_objectives, sibling_programs
from app.services.ge_strategic_lifecycle import refresh_lifecycle_on_read


def _project_rows(visible: list[GeProject]) -> list[dict[str, Any]]:
    return [
        {
            "id": proj.id,
            "name": proj.name,
            "program_id": proj.program_id,
            "pm_user_id": proj.pm_user_id,
            "lifecycle_status": proj.status,
            "status": proj.status,
        }
        for proj in visible
    ]


def _load_projects_for_programs(db: Session, program_ids: list[str]) -> list[GeProject]:
    if not program_ids:
        return []
    return (
        db.query(GeProject)
        .filter(
            GeProject.program_id.in_(program_ids),
            GeProject.deleted_at.is_(None),
        )
        .order_by(GeProject.program_id, GeProject.sort_order, GeProject.name)
        .all()
    )


def _board_for_sub(db: Session, objective_id: str, user: AuthUser) -> dict[str, Any]:
    projection = compute_personal_tree_sets(db, user)
    programs = [
        p for p in sibling_programs(db, objective_id) if p.id in projection.program_ids
    ]
    for prog in programs:
        refresh_lifecycle_on_read(db, prog)

    program_ids = [p.id for p in programs]
    projects = _load_projects_for_programs(db, program_ids)
    visible = filter_projects_for_user(db, projects, user)

    return {
        "objective_id": objective_id,
        "level": "sub",
        "programs": [
            {
                "id": p.id,
                "name": p.name,
                "sort_order": int(p.sort_order or 0),
            }
            for p in programs
        ],
        "projects": _project_rows(visible),
    }


def _board_for_company(db: Session, objective_id: str, user: AuthUser) -> dict[str, Any]:
    """Direct subs + their programs/projects (projection-filtered)."""
    projection = compute_personal_tree_sets(db, user)
    children = sibling_objectives(db, objective_id)
    subs = [
        c
        for c in children
        if str(c.level or "") == "sub" and c.id in projection.objective_ids
    ]
    for sub in subs:
        refresh_lifecycle_on_read(db, sub)

    programs: list[GeProgram] = []
    for sub in subs:
        for prog in sibling_programs(db, sub.id):
            if prog.id not in projection.program_ids:
                continue
            refresh_lifecycle_on_read(db, prog)
            programs.append(prog)

    program_ids = [p.id for p in programs]
    projects = _load_projects_for_programs(db, program_ids)
    visible = filter_projects_for_user(db, projects, user)

    return {
        "objective_id": objective_id,
        "level": "company",
        "subs": [
            {
                "id": s.id,
                "name": s.name,
                "sort_order": int(s.sort_order or 0),
                "owner_user_id": s.owner_user_id,
            }
            for s in subs
        ],
        "programs": [
            {
                "id": p.id,
                "name": p.name,
                "sort_order": int(p.sort_order or 0),
                "sub_objective_id": p.objective_id,
            }
            for p in programs
        ],
        "projects": _project_rows(visible),
    }


def get_objective_board_projects(
    db: Session,
    objective_id: str,
    user: AuthUser,
) -> dict[str, Any]:
    """Return board-projects payload for sub (§4.11) or company (§4.12).

    Normative (GE-VIS-1):
    - missing or outside personal_tree → 404 ``not_found``
    - ``level=sub|company`` → 200; other levels → 400
    - ``programs[]`` ⊆ personal_tree; projects via ``filter_projects_for_user``
    """
    root = db.get(GeObjective, objective_id)
    if root is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if not objective_in_projection(db, user, objective_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    refresh_lifecycle_on_read(db, root)

    level = str(root.level or "")
    if level == "sub":
        return _board_for_sub(db, objective_id, user)
    if level == "company":
        return _board_for_company(db, objective_id, user)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "detail": "objective_level_unsupported",
            "reason": "board_projects_requires_level_sub_or_company",
        },
    )
