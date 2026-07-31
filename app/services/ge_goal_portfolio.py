"""Goal portfolio read API (M31 · §4.1.5).

ORG-PERF.1 / GE-PERF-05: set-based rollup — no per-user
``user_accountable_for_user_id`` loops.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.ge import GeObjective, GeProgram, GeProject, GeTask
from app.models.org import OrgDepartment, OrgTeam, UserOrgMembership
from app.services.ge_accountability import (
    collect_accountable_entries,
    display_name,
    filter_objectives,
    is_archived_entity,
    portfolio_item_from_accountable,
    user_ids_in_team,
)
from app.services.ge_strategic import planning_year_from_start
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


def _contributing_from_tasks(
    projects: list[GeProject],
    tasks: list[GeTask],
) -> list[dict[str, Any]]:
    """Same shape as collect_contributing_entries, without an extra SQL round-trip."""
    if not projects:
        return []
    pm_by_project = {p.id: p.pm_user_id for p in projects}
    name_by_project = {p.id: p.name for p in projects}
    project_ids = set(pm_by_project)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for task in tasks:
        if task.project_id not in project_ids:
            continue
        uid = task.assignee_user_id
        if not uid or uid == pm_by_project.get(task.project_id):
            continue
        counts[uid][task.project_id] += 1
    contributing: list[dict[str, Any]] = []
    for uid, proj_counts in sorted(counts.items()):
        contributing.append(
            {
                "user_id": uid,
                "display_name": display_name(uid),
                "projects": [
                    {
                        "project_id": pid,
                        "project_name": name_by_project[pid],
                        "task_count": count,
                    }
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
    accountable_entries = collect_accountable_entries(objectives, programs, pm_projects)

    project_ids = [p.id for p in projects]
    tasks = (
        db.query(GeTask).filter(GeTask.project_id.in_(project_ids)).all() if project_ids else []
    )
    # Contributing projects: those with a non-PM assignee in user_ids (prior semantics
    # used the union of such projects, then expanded to all non-PM assignees on them).
    contrib_project_ids = {
        t.project_id
        for t in tasks
        if t.assignee_user_id in user_ids
        and t.assignee_user_id
        and t.assignee_user_id != next((p.pm_user_id for p in projects if p.id == t.project_id), None)
    }
    contrib_projects = [p for p in projects if p.id in contrib_project_ids]
    return (
        _group_accountable(accountable_entries),
        _contributing_from_tasks(contrib_projects, tasks),
    )


def _filter_primary(primary: list[dict[str, Any]], *, include_archived: bool) -> list[dict[str, Any]]:
    if include_archived:
        return primary
    return [p for p in primary if (p.get("lifecycle_status") or "active") != "archived"]


def _department_subtree_ids_from_rows(
    all_depts: list[OrgDepartment], department_id: str
) -> set[str]:
    children_by_parent: dict[str | None, list[str]] = defaultdict(list)
    for dept in all_depts:
        children_by_parent[dept.parent_id].append(dept.id)
    ids: set[str] = {department_id}
    queue = [department_id]
    while queue:
        parent = queue.pop()
        for child_id in children_by_parent.get(parent, []):
            if child_id not in ids:
                ids.add(child_id)
                queue.append(child_id)
    return ids


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
    include_completed: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    all_depts = db.query(OrgDepartment).all()
    if not any(d.id == department_id for d in all_depts):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})

    subtree_ids = _department_subtree_ids_from_rows(all_depts, department_id)
    member_rows = (
        db.query(UserOrgMembership.user_id)
        .filter(UserOrgMembership.department_id.in_(list(subtree_ids)))
        .distinct()
        .all()
    )
    user_ids = {r[0] for r in member_rows}
    uid_list = list(user_ids)

    obj_clauses = [GeObjective.primary_department_id == department_id]
    if uid_list:
        obj_clauses.append(GeObjective.owner_user_id.in_(uid_list))
    objectives = (
        db.query(GeObjective).filter(GeObjective.is_default.is_(False), or_(*obj_clauses)).all()
    )

    prog_clauses = [GeProgram.primary_department_id == department_id]
    if uid_list:
        prog_clauses.append(GeProgram.owner_user_id.in_(uid_list))
    programs = db.query(GeProgram).filter(GeProgram.is_default.is_(False), or_(*prog_clauses)).all()

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

    acc_objectives = filter_objectives(
        [o for o in objectives if o.owner_user_id in user_ids],
        include_archived=include_archived,
    )
    acc_programs = [
        p
        for p in programs
        if p.owner_user_id in user_ids and (include_archived or not is_archived_entity(p))
    ]

    # Single JOIN covers PM + assignee projects and assignee rows for contributing
    row_q = (
        db.query(
            GeProject.id,
            GeProject.name,
            GeProject.pm_user_id,
            GeProject.status,
            GeTask.id,
            GeTask.assignee_user_id,
            GeTask.project_id,
        )
        .outerjoin(GeTask, GeTask.project_id == GeProject.id)
        .filter(
            GeProject.deleted_at.is_(None),
            or_(
                GeProject.pm_user_id.in_(uid_list),
                GeTask.assignee_user_id.in_(uid_list),
            ),
        )
    )
    if not include_completed:
        row_q = row_q.filter(GeProject.status != "completed")
    rows = row_q.all()

    projects_by_id: dict[str, GeProject] = {}
    tasks: list[GeTask] = []
    seen_task_ids: set[str] = set()
    for pid, pname, pm, status_val, task_id, assignee, task_pid in rows:
        if pid not in projects_by_id:
            projects_by_id[pid] = GeProject(
                id=pid,
                name=pname,
                pm_user_id=pm,
                status=status_val,
            )
        if task_id and task_id not in seen_task_ids:
            seen_task_ids.add(task_id)
            tasks.append(
                GeTask(id=task_id, assignee_user_id=assignee, project_id=task_pid or pid)
            )

    projects = list(projects_by_id.values())
    pm_projects = [p for p in projects if p.pm_user_id in user_ids]
    accountable_entries = collect_accountable_entries(acc_objectives, acc_programs, pm_projects)

    pm_by = {p.id: p.pm_user_id for p in projects}
    contrib_ids = {
        t.project_id
        for t in tasks
        if t.assignee_user_id in user_ids
        and t.assignee_user_id
        and t.assignee_user_id != pm_by.get(t.project_id)
    }
    contrib_projects = [p for p in projects if p.id in contrib_ids]

    return _portfolio_payload(
        primary=primary,
        accountable=_group_accountable(accountable_entries),
        contributing=_contributing_from_tasks(contrib_projects, tasks),
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
