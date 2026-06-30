"""Sibling sort_order for GE objectives, programs, and projects (M32)."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_strategic_period import LIFECYCLE_ACTIVE

ReorderDirection = Literal["up", "down"]


def _objective_sort_key(obj: GeObjective) -> tuple[int, str]:
    return (obj.sort_order, obj.name)


def _program_sort_key(program: GeProgram) -> tuple[int, str]:
    return (program.sort_order, program.name)


def _project_sort_key(project: GeProject) -> tuple[int, str]:
    return (project.sort_order, project.name)


def sibling_objectives(db: Session, parent_id: str | None) -> list[GeObjective]:
    query = db.query(GeObjective)
    if parent_id is None:
        query = query.filter(GeObjective.parent_id.is_(None))
    else:
        query = query.filter(GeObjective.parent_id == parent_id)
    return sorted(query.all(), key=_objective_sort_key)


def sibling_programs(db: Session, objective_id: str) -> list[GeProgram]:
    programs = db.query(GeProgram).filter(GeProgram.objective_id == objective_id).all()
    return sorted(programs, key=_program_sort_key)


def sibling_projects(db: Session, program_id: str) -> list[GeProject]:
    projects = (
        db.query(GeProject)
        .filter(GeProject.program_id == program_id, GeProject.deleted_at.is_(None))
        .all()
    )
    return sorted(projects, key=_project_sort_key)


def next_objective_sort_order(db: Session, parent_id: str | None) -> int:
    siblings = sibling_objectives(db, parent_id)
    if not siblings:
        return 10
    return max(obj.sort_order for obj in siblings) + 10


def next_program_sort_order(db: Session, objective_id: str) -> int:
    siblings = sibling_programs(db, objective_id)
    if not siblings:
        return 10
    return max(program.sort_order for program in siblings) + 10


def next_project_sort_order(db: Session, program_id: str) -> int:
    siblings = sibling_projects(db, program_id)
    if not siblings:
        return 10
    return max(project.sort_order for project in siblings) + 10


def _normalize_objective_orders(objectives: list[GeObjective]) -> None:
    for index, obj in enumerate(objectives):
        obj.sort_order = (index + 1) * 10


def _normalize_program_orders(programs: list[GeProgram]) -> None:
    for index, program in enumerate(programs):
        program.sort_order = (index + 1) * 10


def _normalize_project_orders(projects: list[GeProject]) -> None:
    for index, project in enumerate(projects):
        project.sort_order = (index + 1) * 10


def _assert_objective_reorderable(obj: GeObjective) -> None:
    if obj.is_default:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "default_node_immutable"})
    if (obj.lifecycle_status or LIFECYCLE_ACTIVE) != LIFECYCLE_ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "strategic_locked"})


def _assert_program_reorderable(program: GeProgram) -> None:
    if program.is_default:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "default_node_immutable"})
    if (program.lifecycle_status or LIFECYCLE_ACTIVE) != LIFECYCLE_ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "strategic_locked"})


def reorder_objective(db: Session, objective_id: str, direction: ReorderDirection) -> GeObjective:
    obj = db.get(GeObjective, objective_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    _assert_objective_reorderable(obj)
    siblings = sibling_objectives(db, obj.parent_id)
    index = next((i for i, item in enumerate(siblings) if item.id == objective_id), -1)
    if index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if direction == "up":
        if index == 0:
            return obj
        siblings[index], siblings[index - 1] = siblings[index - 1], siblings[index]
    elif direction == "down":
        if index >= len(siblings) - 1:
            return obj
        siblings[index], siblings[index + 1] = siblings[index + 1], siblings[index]
    _normalize_objective_orders(siblings)
    return obj


def reorder_program(db: Session, program_id: str, direction: ReorderDirection) -> GeProgram:
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    _assert_program_reorderable(program)
    siblings = sibling_programs(db, program.objective_id)
    index = next((i for i, item in enumerate(siblings) if item.id == program_id), -1)
    if index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if direction == "up":
        if index == 0:
            return program
        siblings[index], siblings[index - 1] = siblings[index - 1], siblings[index]
    elif direction == "down":
        if index >= len(siblings) - 1:
            return program
        siblings[index], siblings[index + 1] = siblings[index + 1], siblings[index]
    _normalize_program_orders(siblings)
    return program


def reorder_project(db: Session, project_id: str, direction: ReorderDirection) -> GeProject:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    siblings = sibling_projects(db, project.program_id)
    index = next((i for i, item in enumerate(siblings) if item.id == project_id), -1)
    if index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if direction == "up":
        if index == 0:
            return project
        siblings[index], siblings[index - 1] = siblings[index - 1], siblings[index]
    elif direction == "down":
        if index >= len(siblings) - 1:
            return project
        siblings[index], siblings[index + 1] = siblings[index + 1], siblings[index]
    _normalize_project_orders(siblings)
    return project


def annual_root_sort_key(obj: GeObjective) -> tuple[int, int, str]:
    """Annual company roots: year DESC; default chain last."""
    if obj.is_default:
        return (1, 0, obj.name)
    year = 0
    if obj.period_start and len(obj.period_start) >= 4:
        try:
            year = int(obj.period_start[:4])
        except ValueError:
            year = 0
    return (0, -year, obj.name)
