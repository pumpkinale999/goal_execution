"""Goal portfolio read API (M31 · §4.1.5).

ORG-PERF.1 / GE-PERF-05: set-based rollup — no per-user
``user_accountable_for_user_id`` loops.

ORG-DEPT-GE-VAL-F1: department/team portfolio must not read GE org_* tables;
member scope comes from BFF via ``member_user_ids``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.ge import GeObjective, GeProgram, GeProject, GeTask
from app.services.ge_accountability import (
    collect_accountable_entries,
    display_name,
    filter_objectives,
    is_archived_entity,
    portfolio_item_from_accountable,
    program_names_for_projects,
    _contributing_project_row,
)
from app.services.ge_strategic import planning_year_from_start
from app.services.ge_strategic_lifecycle import refresh_lifecycle_on_read


def _normalize_member_user_ids(member_user_ids: Iterable[str] | None) -> set[str]:
    if not member_user_ids:
        return set()
    return {str(u).strip() for u in member_user_ids if str(u).strip()}


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


def _contributing_from_tasks(
    projects: list[GeProject],
    tasks: list[GeTask],
    *,
    program_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Same shape as collect_contributing_entries, without an extra SQL round-trip."""
    if not projects:
        return []
    names = program_names or {}
    name_by_project = {p.id: p.name for p in projects}
    program_id_by_project = {p.id: p.program_id for p in projects}
    project_ids = {p.id for p in projects}
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for task in tasks:
        if task.project_id not in project_ids:
            continue
        uid = task.assignee_user_id
        if not uid:
            continue
        # DESK-GE1 MS5: include PM when they hold assignee tasks (dual-fill).
        counts[uid][task.project_id] += 1
    contributing: list[dict[str, Any]] = []
    for uid, proj_counts in sorted(counts.items()):
        contributing.append(
            {
                "user_id": uid,
                "display_name": display_name(uid),
                "projects": [
                    _contributing_project_row(
                        pid,
                        project_name=name_by_project[pid],
                        program_id=program_id_by_project.get(pid),
                        program_names=names,
                        task_count=count,
                    )
                    for pid, count in sorted(proj_counts.items())
                ],
            }
        )
    return contributing


def _rollup_for_users(
    db: Session,
    user_ids: set[str],
    *,
    include_completed: bool,
    include_archived: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not user_ids:
        return [], []

    uid_list = list(user_ids)

    objectives = (
        db.query(GeObjective)
        .filter(GeObjective.owner_user_id.in_(uid_list), GeObjective.is_default.is_(False))
        .all()
    )
    programs = (
        db.query(GeProgram)
        .filter(GeProgram.owner_user_id.in_(uid_list), GeProgram.is_default.is_(False))
        .all()
    )
    projects_q = db.query(GeProject).filter(
        GeProject.deleted_at.is_(None),
        or_(
            GeProject.pm_user_id.in_(uid_list),
            GeProject.id.in_(
                db.query(GeTask.project_id).filter(GeTask.assignee_user_id.in_(uid_list))
            ),
        ),
    )
    if not include_completed:
        projects_q = projects_q.filter(GeProject.status != "completed")
    projects = projects_q.all()

    for obj in objectives:
        refresh_lifecycle_on_read(db, obj)
    for prog in programs:
        refresh_lifecycle_on_read(db, prog)

    objectives = filter_objectives(objectives, include_archived=include_archived)
    programs = [p for p in programs if include_archived or not is_archived_entity(p)]
    pm_projects = [p for p in projects if p.pm_user_id in user_ids]
    # One program-name SELECT for all projects in this rollup (PM + contributor).
    program_names = program_names_for_projects(db, projects)
    accountable_entries = collect_accountable_entries(
        objectives, programs, pm_projects, program_names=program_names
    )

    project_ids = [p.id for p in projects]
    tasks = (
        db.query(GeTask).filter(GeTask.project_id.in_(project_ids)).all() if project_ids else []
    )
    contrib_project_ids = {
        t.project_id
        for t in tasks
        if t.assignee_user_id in user_ids and t.assignee_user_id
    }
    contrib_projects = [p for p in projects if p.id in contrib_project_ids]
    return (
        _group_accountable(accountable_entries),
        _contributing_from_tasks(contrib_projects, tasks, program_names=program_names),
    )


def _filter_primary(primary: list[dict[str, Any]], *, include_archived: bool) -> list[dict[str, Any]]:
    if include_archived:
        return primary
    return [p for p in primary if (p.get("lifecycle_status") or "active") != "archived"]


def _primary_from_entities(
    objectives: list[GeObjective],
    programs: list[GeProgram],
    *,
    department_id: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for obj in objectives:
        if obj.primary_department_id != department_id:
            continue
        item: dict[str, Any] = {
            "node_type": "objective",
            "node_id": obj.id,
            "node_name": obj.name,
            "lifecycle_status": obj.lifecycle_status,
        }
        if obj.level == "company" and not obj.is_default:
            item["planning_year"] = planning_year_from_start(obj.period_start)
        entries.append(item)
    for prog in programs:
        if prog.primary_department_id != department_id:
            continue
        entries.append(
            {
                "node_type": "program",
                "node_id": prog.id,
                "node_name": prog.name,
                "lifecycle_status": prog.lifecycle_status,
            }
        )
    return entries


def get_department_goal_portfolio(
    db: Session,
    department_id: str,
    *,
    member_user_ids: Iterable[str] | None = None,
    include_completed: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Primary by exact department_id; participation from injected member_user_ids only."""
    user_ids = _normalize_member_user_ids(member_user_ids)

    objectives = (
        db.query(GeObjective)
        .filter(
            GeObjective.is_default.is_(False),
            GeObjective.primary_department_id == department_id,
        )
        .all()
    )
    programs = (
        db.query(GeProgram)
        .filter(
            GeProgram.is_default.is_(False),
            GeProgram.primary_department_id == department_id,
        )
        .all()
    )
    for obj in objectives:
        refresh_lifecycle_on_read(db, obj)
    for prog in programs:
        refresh_lifecycle_on_read(db, prog)

    primary = _filter_primary(
        _primary_from_entities(objectives, programs, department_id=department_id),
        include_archived=include_archived,
    )

    if not user_ids:
        return _portfolio_payload(
            primary=primary,
            accountable=[],
            contributing=[],
            include_completed=include_completed,
            include_archived=include_archived,
        )

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
    member_user_ids: Iterable[str] | None = None,
    include_completed: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    _ = team_id  # identity for route/authz; membership resolved by BFF
    user_ids = _normalize_member_user_ids(member_user_ids)
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
