"""Projects for a set of users within a period window (PBC mode-H hint list).

own = project.pm_user_id
manage = user owns program / objective ancestor that the project hangs under
"""

from __future__ import annotations

import calendar
from typing import Any

from sqlalchemy.orm import Session

from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_access import _governed_program_ids_for_user
from app.services.ge_accountability import projects_for_programs
from app.services.ge_schedule_derive import build_program_period


def quarter_bounds(year: int, quarter: int) -> tuple[str, str]:
    if quarter < 1 or quarter > 4:
        raise ValueError("invalid_quarter")
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    last_day = calendar.monthrange(year, end_month)[1]
    return (
        f"{year}-{start_month:02d}-01",
        f"{year}-{end_month:02d}-{last_day:02d}",
    )


def _periods_intersect(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    return a_start <= b_end and a_end >= b_start


def projects_for_users_in_period(
    db: Session,
    *,
    user_ids: list[str],
    period_start: str,
    period_end: str,
    include_completed: bool = True,
) -> list[dict[str, Any]]:
    """Return deduped projects related to users in [period_start, period_end].

    Each item: project_id, name, status, program_id, program_name, pm_user_id,
    relation (own|manage), related_user_ids, period_start, period_end.
    When both own and manage apply for different users, relation prefers own;
    related_user_ids lists all matching users.
    """
    uids = sorted({str(u).strip() for u in user_ids if str(u).strip()})
    if not uids:
        return []

    # own: PM
    pm_rows = (
        db.query(GeProject)
        .filter(
            GeProject.pm_user_id.in_(uids),
            GeProject.deleted_at.is_(None),
        )
        .all()
    )
    if not include_completed:
        pm_rows = [p for p in pm_rows if p.status != "completed"]

    # manage: governed programs → projects
    governed_by_user: dict[str, set[str]] = {}
    all_governed: set[str] = set()
    for uid in uids:
        prog_ids = _governed_program_ids_for_user(db, uid)
        governed_by_user[uid] = prog_ids
        all_governed |= prog_ids

    managed_rows = projects_for_programs(
        db, sorted(all_governed), include_completed=include_completed
    )

    by_id: dict[str, GeProject] = {}
    for p in pm_rows:
        by_id[p.id] = p
    for p in managed_rows:
        by_id[p.id] = p

    if not by_id:
        return []

    program_ids = {p.program_id for p in by_id.values() if p.program_id}
    programs = {
        prog.id: prog
        for prog in db.query(GeProgram).filter(GeProgram.id.in_(program_ids)).all()
    }
    objective_ids = {prog.objective_id for prog in programs.values() if prog.objective_id}
    objectives = {
        obj.id: obj
        for obj in db.query(GeObjective).filter(GeObjective.id.in_(objective_ids)).all()
    } if objective_ids else {}

    # project_id -> {relation preference, related users, period}
    acc: dict[str, dict[str, Any]] = {}
    for project in by_id.values():
        program = programs.get(project.program_id) if project.program_id else None
        objective = objectives.get(program.objective_id) if program and program.objective_id else None
        resolved = build_program_period(program, objective=objective)
        if not resolved:
            continue
        p_start = str(resolved["period_start"])
        p_end = str(resolved["period_end"])
        if not _periods_intersect(p_start, p_end, period_start, period_end):
            continue

        related: list[str] = []
        has_own = False
        has_manage = False
        pm = str(project.pm_user_id or "").strip()
        if pm in uids:
            has_own = True
            related.append(pm)
        for uid in uids:
            if uid == pm:
                continue
            if project.program_id and project.program_id in governed_by_user.get(uid, set()):
                has_manage = True
                related.append(uid)

        if not has_own and not has_manage:
            continue

        relation = "own" if has_own else "manage"
        # If PM is also in manage set for others, still own; related already has all.
        # Also flag manage-only users when PM is in pool: relation stays own.
        if has_own and has_manage:
            relation = "own"

        acc[project.id] = {
            "project_id": project.id,
            "name": project.name,
            "status": project.status,
            "program_id": project.program_id,
            "program_name": program.name if program else None,
            "pm_user_id": project.pm_user_id,
            "relation": relation,
            "related_user_ids": related,
            "period_start": p_start,
            "period_end": p_end,
        }

    return sorted(acc.values(), key=lambda row: (row["name"] or "", row["project_id"]))
