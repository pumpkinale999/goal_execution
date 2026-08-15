"""People summary read API (M30 · §4.2.4 · program/project)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeProgram, GeProject
from app.services.ge_access import can_read_project
from app.services.ge_accountability import (
    can_read_program_scope,
    collect_accountable_entries,
    collect_contributing_entries,
    projects_for_programs,
)
from app.services.ge_strategic_lifecycle import refresh_lifecycle_on_read


def _people_summary_payload(
    *,
    accountable: list[dict[str, Any]],
    contributing: list[dict[str, Any]],
    include_completed: bool,
) -> dict[str, Any]:
    return {
        "accountable": accountable,
        "contributing": contributing,
        "include_completed": include_completed,
    }


def get_program_people_summary(
    db: Session,
    program_id: str,
    user: AuthUser,
    *,
    include_completed: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if not can_read_program_scope(db, user, program_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "forbidden"})

    refresh_lifecycle_on_read(db, program)
    if include_archived or (program.lifecycle_status or "active") != "archived":
        programs = [program]
    else:
        programs = []
    projects = projects_for_programs(db, [program_id], include_completed=include_completed)

    return _people_summary_payload(
        accountable=collect_accountable_entries([], programs, projects),
        contributing=collect_contributing_entries(db, projects),
        include_completed=include_completed,
    )


def get_project_people_summary(
    db: Session,
    project_id: str,
    user: AuthUser,
    *,
    include_completed: bool = False,
) -> dict[str, Any]:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "forbidden"})

    if include_completed or project.status != "completed":
        projects = [project]
    else:
        projects = []

    return _people_summary_payload(
        accountable=collect_accountable_entries([], [], projects),
        contributing=collect_contributing_entries(db, projects),
        include_completed=include_completed,
    )
