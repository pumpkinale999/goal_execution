"""Sibling sort_order for org departments and teams."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.org import OrgDepartment, OrgTeam

ReorderDirection = Literal["up", "down"]


def _dept_sort_key(dept: OrgDepartment) -> tuple[int, str]:
    return (dept.sort_order, dept.name)


def _team_sort_key(team: OrgTeam) -> tuple[int, str]:
    return (team.sort_order, team.name)


def sibling_departments(db: Session, parent_id: str | None) -> list[OrgDepartment]:
    query = db.query(OrgDepartment)
    if parent_id is None:
        query = query.filter(OrgDepartment.parent_id.is_(None))
    else:
        query = query.filter(OrgDepartment.parent_id == parent_id)
    return sorted(query.all(), key=_dept_sort_key)


def sibling_teams(db: Session, department_id: str) -> list[OrgTeam]:
    teams = db.query(OrgTeam).filter(OrgTeam.department_id == department_id).all()
    return sorted(teams, key=_team_sort_key)


def next_department_sort_order(db: Session, parent_id: str | None) -> int:
    siblings = sibling_departments(db, parent_id)
    if not siblings:
        return 10
    return max(dept.sort_order for dept in siblings) + 10


def next_team_sort_order(db: Session, department_id: str) -> int:
    siblings = sibling_teams(db, department_id)
    if not siblings:
        return 10
    return max(team.sort_order for team in siblings) + 10


def _normalize_department_orders(depts: list[OrgDepartment]) -> None:
    for index, dept in enumerate(depts):
        dept.sort_order = (index + 1) * 10


def _normalize_team_orders(teams: list[OrgTeam]) -> None:
    for index, team in enumerate(teams):
        team.sort_order = (index + 1) * 10


def reorder_department(db: Session, department_id: str, direction: ReorderDirection) -> OrgDepartment:
    dept = db.get(OrgDepartment, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    siblings = sibling_departments(db, dept.parent_id)
    index = next((i for i, item in enumerate(siblings) if item.id == department_id), -1)
    if index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if direction == "up":
        if index == 0:
            return dept
        siblings[index], siblings[index - 1] = siblings[index - 1], siblings[index]
    elif direction == "down":
        if index >= len(siblings) - 1:
            return dept
        siblings[index], siblings[index + 1] = siblings[index + 1], siblings[index]
    _normalize_department_orders(siblings)
    return dept


def reorder_team(db: Session, team_id: str, direction: ReorderDirection) -> OrgTeam:
    team = db.get(OrgTeam, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    siblings = sibling_teams(db, team.department_id)
    index = next((i for i, item in enumerate(siblings) if item.id == team_id), -1)
    if index < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if direction == "up":
        if index == 0:
            return team
        siblings[index], siblings[index - 1] = siblings[index - 1], siblings[index]
    elif direction == "down":
        if index >= len(siblings) - 1:
            return team
        siblings[index], siblings[index + 1] = siblings[index + 1], siblings[index]
    _normalize_team_orders(siblings)
    return team
