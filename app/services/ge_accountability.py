"""Accountable / contributing rollup (M30/M31 · §3.3.9)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeObjective, GeProgram, GeProject, GeTask
from app.services.ge_access import can_read_project, is_participant
from app.services.ge_strategic import planning_year_from_start
from app.services.ge_strategic_lifecycle import refresh_lifecycle_on_read
from app.services.ge_strategic_period import LIFECYCLE_ARCHIVED
from app.services.ge_subtree_governor import is_subtree_governor


def display_name(user_id: str | None) -> str:
    return str(user_id or "").strip()


def is_archived_entity(entity: GeObjective | GeProgram) -> bool:
    return (entity.lifecycle_status or "active") == LIFECYCLE_ARCHIVED


def objective_descendant_ids(db: Session, root_id: str) -> list[str]:
    ids = [root_id]
    queue = [root_id]
    while queue:
        parent_id = queue.pop()
        children = db.query(GeObjective).filter(GeObjective.parent_id == parent_id).all()
        for child in children:
            ids.append(child.id)
            queue.append(child.id)
    return ids


def objectives_in_ids(db: Session, objective_ids: list[str]) -> list[GeObjective]:
    if not objective_ids:
        return []
    return db.query(GeObjective).filter(GeObjective.id.in_(objective_ids)).all()


def programs_for_objectives(
    db: Session,
    objective_ids: list[str],
    *,
    include_archived: bool,
) -> list[GeProgram]:
    if not objective_ids:
        return []
    rows = db.query(GeProgram).filter(GeProgram.objective_id.in_(objective_ids)).all()
    out: list[GeProgram] = []
    for prog in rows:
        refresh_lifecycle_on_read(db, prog)
        if include_archived or not is_archived_entity(prog):
            out.append(prog)
    return out


def projects_for_programs(
    db: Session,
    program_ids: list[str],
    *,
    include_completed: bool,
) -> list[GeProject]:
    if not program_ids:
        return []
    q = db.query(GeProject).filter(
        GeProject.program_id.in_(program_ids),
        GeProject.deleted_at.is_(None),
    )
    if not include_completed:
        q = q.filter(GeProject.status != "completed")
    return q.all()


def collect_accountable_entries(
    objectives: list[GeObjective],
    programs: list[GeProgram],
    projects: list[GeProject],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for obj in objectives:
        if obj.owner_user_id:
            entries.append(
                {
                    "user_id": obj.owner_user_id,
                    "display_name": display_name(obj.owner_user_id),
                    "role": "owner",
                    "node_type": "objective",
                    "node_id": obj.id,
                    "node_name": obj.name,
                }
            )
    for prog in programs:
        if prog.owner_user_id:
            entries.append(
                {
                    "user_id": prog.owner_user_id,
                    "display_name": display_name(prog.owner_user_id),
                    "role": "owner",
                    "node_type": "program",
                    "node_id": prog.id,
                    "node_name": prog.name,
                }
            )
    for project in projects:
        entries.append(
            {
                "user_id": project.pm_user_id,
                "display_name": display_name(project.pm_user_id),
                "role": "pm",
                "node_type": "project",
                "node_id": project.id,
                "node_name": project.name,
            }
        )
    return entries


def collect_contributing_entries(db: Session, projects: list[GeProject]) -> list[dict[str, Any]]:
    if not projects:
        return []
    project_ids = [p.id for p in projects]
    pm_by_project = {p.id: p.pm_user_id for p in projects}
    name_by_project = {p.id: p.name for p in projects}
    tasks = db.query(GeTask).filter(GeTask.project_id.in_(project_ids)).all()
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for task in tasks:
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


def refresh_objectives_in_subtree(db: Session, root_id: str) -> list[GeObjective]:
    ids = objective_descendant_ids(db, root_id)
    objectives = objectives_in_ids(db, ids)
    for obj in objectives:
        refresh_lifecycle_on_read(db, obj)
    return objectives


def filter_objectives(objectives: list[GeObjective], *, include_archived: bool) -> list[GeObjective]:
    if include_archived:
        return objectives
    return [o for o in objectives if not is_archived_entity(o)]


def primary_entries_for_department(db: Session, department_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    objectives = (
        db.query(GeObjective)
        .filter(GeObjective.primary_department_id == department_id, GeObjective.is_default == 0)
        .all()
    )
    for obj in objectives:
        refresh_lifecycle_on_read(db, obj)
        item: dict[str, Any] = {
            "node_type": "objective",
            "node_id": obj.id,
            "node_name": obj.name,
            "lifecycle_status": obj.lifecycle_status,
        }
        if obj.level == "company" and not obj.is_default:
            item["planning_year"] = planning_year_from_start(obj.period_start)
        entries.append(item)
    programs = (
        db.query(GeProgram)
        .filter(GeProgram.primary_department_id == department_id, GeProgram.is_default == 0)
        .all()
    )
    for prog in programs:
        refresh_lifecycle_on_read(db, prog)
        entries.append(
            {
                "node_type": "program",
                "node_id": prog.id,
                "node_name": prog.name,
                "lifecycle_status": prog.lifecycle_status,
            }
        )
    return entries


def portfolio_item_from_accountable(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_type": entry["node_type"],
        "node_id": entry["node_id"],
        "node_name": entry["node_name"],
        "role": entry["role"],
    }


def can_read_objective_scope(db: Session, user: AuthUser, objective_id: str) -> bool:
    if user.auth_method == "service":
        return True
    if is_subtree_governor(db, user_id=user.user_id, objective_id=objective_id):
        return True
    obj_ids = objective_descendant_ids(db, objective_id)
    programs = db.query(GeProgram).filter(GeProgram.objective_id.in_(obj_ids)).all()
    program_ids = [p.id for p in programs]
    projects = projects_for_programs(db, program_ids, include_completed=True)
    for project in projects:
        if can_read_project(db, project, user):
            return True
    return False


def can_read_program_scope(db: Session, user: AuthUser, program_id: str) -> bool:
    if user.auth_method == "service":
        return True
    if is_subtree_governor(db, user_id=user.user_id, program_id=program_id):
        return True
    projects = projects_for_programs(db, [program_id], include_completed=True)
    return any(can_read_project(db, p, user) for p in projects)


def user_accountable_for_user_id(db: Session, user_id: str) -> tuple[list[GeObjective], list[GeProgram], list[GeProject]]:
    objectives = (
        db.query(GeObjective)
        .filter(GeObjective.owner_user_id == user_id, GeObjective.is_default == 0)
        .all()
    )
    programs = (
        db.query(GeProgram)
        .filter(GeProgram.owner_user_id == user_id, GeProgram.is_default == 0)
        .all()
    )
    projects = (
        db.query(GeProject)
        .filter(GeProject.pm_user_id == user_id, GeProject.deleted_at.is_(None))
        .all()
    )
    for obj in objectives:
        refresh_lifecycle_on_read(db, obj)
    for prog in programs:
        refresh_lifecycle_on_read(db, prog)
    return objectives, programs, projects


def user_contributing_projects(db: Session, user_id: str, *, include_completed: bool) -> list[GeProject]:
    q = (
        db.query(GeProject)
        .join(GeTask, GeTask.project_id == GeProject.id)
        .filter(
            GeTask.assignee_user_id == user_id,
            GeProject.deleted_at.is_(None),
            GeProject.pm_user_id != user_id,
        )
    )
    if not include_completed:
        q = q.filter(GeProject.status != "completed")
    return q.distinct().all()


def department_subtree_ids(db: Session, department_id: str) -> set[str]:
    from app.models.org import OrgDepartment

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


def user_ids_in_departments(db: Session, department_ids: set[str]) -> set[str]:
    from app.models.org import UserOrgMembership

    if not department_ids:
        return set()
    rows = (
        db.query(UserOrgMembership.user_id)
        .filter(UserOrgMembership.department_id.in_(department_ids))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def user_ids_in_team(db: Session, team_id: str) -> set[str]:
    from app.models.org import UserOrgMembership

    rows = db.query(UserOrgMembership.user_id).filter(UserOrgMembership.team_id == team_id).all()
    return {r[0] for r in rows}


def is_user_participant_in_subtree(db: Session, user_id: str, objective_id: str) -> bool:
    obj_ids = objective_descendant_ids(db, objective_id)
    programs = db.query(GeProgram).filter(GeProgram.objective_id.in_(obj_ids)).all()
    projects = projects_for_programs(db, [p.id for p in programs], include_completed=True)
    return any(is_participant(db, p, user_id) for p in projects)
