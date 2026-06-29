"""Goal portfolio read API (M31 · §4.1.5)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.org import OrgDepartment, OrgTeam
from app.services.ge_accountability import (
    collect_accountable_entries,
    collect_contributing_entries,
    display_name,
    filter_objectives,
    is_archived_entity,
    portfolio_item_from_accountable,
    primary_entries_for_department,
    programs_for_objectives,
    projects_for_programs,
    user_accountable_for_user_id,
    user_contributing_projects,
    user_ids_in_departments,
    user_ids_in_team,
)
from app.services.ge_strategic_lifecycle import refresh_lifecycle_on_read


def _portfolio_payload(
    *,
    primary: list[dict[str, Any]] | None,
    accountable: list[dict[str, Any]],
    contributing: list[dict[str, Any]],
    include_completed: bool,
    include_archived: bool,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "accountable": accountable,
        "contributing": contributing,
        "include_completed": include_completed,
        "include_archived": include_archived,
    }
    if primary is not None:
        out["primary"] = primary
    return out


def _group_accountable(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_user[entry["user_id"]].append(portfolio_item_from_accountable(entry))
    grouped: list[dict[str, Any]] = []
    for uid in sorted(by_user):
        grouped.append(
            {
                "user_id": uid,
                "display_name": display_name(uid),
                "items": by_user[uid],
            }
        )
    return grouped


def _rollup_for_users(
    db: Session,
    user_ids: set[str],
    *,
    include_completed: bool,
    include_archived: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accountable_entries: list[dict[str, Any]] = []
    contributing_projects: list = []
    seen_projects: set[str] = set()

    for uid in user_ids:
        objectives, programs, projects = user_accountable_for_user_id(db, uid)
        objectives = filter_objectives(objectives, include_archived=include_archived)
        programs = [p for p in programs if include_archived or not is_archived_entity(p)]
        if not include_completed:
            projects = [p for p in projects if p.status != "completed"]
        accountable_entries.extend(collect_accountable_entries(objectives, programs, projects))

        for project in user_contributing_projects(db, uid, include_completed=include_completed):
            if project.id not in seen_projects:
                seen_projects.add(project.id)
                contributing_projects.append(project)

    return (
        _group_accountable(accountable_entries),
        collect_contributing_entries(db, contributing_projects),
    )


def _filter_primary(primary: list[dict[str, Any]], *, include_archived: bool) -> list[dict[str, Any]]:
    if include_archived:
        return primary
    return [p for p in primary if (p.get("lifecycle_status") or "active") != "archived"]


def get_department_goal_portfolio(
    db: Session,
    department_id: str,
    *,
    include_completed: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    dept = db.get(OrgDepartment, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})

    primary = _filter_primary(
        primary_entries_for_department(db, department_id),
        include_archived=include_archived,
    )
    subtree_ids = _department_subtree_ids(db, department_id)
    user_ids = user_ids_in_departments(db, subtree_ids)
    accountable, contributing = _rollup_for_users(
        db,
        user_ids,
        include_completed=include_completed,
        include_archived=include_archived,
    )
    return _portfolio_payload(
        primary=primary,
        accountable=accountable,
        contributing=contributing,
        include_completed=include_completed,
        include_archived=include_archived,
    )


def get_team_goal_portfolio(
    db: Session,
    team_id: str,
    *,
    include_completed: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    team = db.get(OrgTeam, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})

    user_ids = user_ids_in_team(db, team_id)
    accountable, contributing = _rollup_for_users(
        db,
        user_ids,
        include_completed=include_completed,
        include_archived=include_archived,
    )
    return _portfolio_payload(
        primary=None,
        accountable=accountable,
        contributing=contributing,
        include_completed=include_completed,
        include_archived=include_archived,
    )


def get_user_goal_portfolio(
    db: Session,
    user_id: str,
    *,
    include_completed: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    accountable, contributing = _rollup_for_users(
        db,
        {user_id},
        include_completed=include_completed,
        include_archived=include_archived,
    )
    return _portfolio_payload(
        primary=None,
        accountable=accountable,
        contributing=contributing,
        include_completed=include_completed,
        include_archived=include_archived,
    )


def _department_subtree_ids(db: Session, department_id: str) -> set[str]:
    ids: set[str] = {department_id}
    queue = [department_id]
    while queue:
        parent = queue.pop()
        children = db.query(OrgDepartment).filter(OrgDepartment.parent_id == parent).all()
        for child in children:
            if child.id not in ids:
                ids.add(child.id)
                queue.append(child.id)
    return ids
