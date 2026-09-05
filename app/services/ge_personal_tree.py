"""Personal left-tree projection (GE-VIS-1).

Normative: platform-docs/目标与执行-个人左树投影迭代.md §3.1 / appendix C.

personal_tree = governed subtree ∪ (execution-anchor projects + ancestors).
Reviewers get the full tree (caller skips this module).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.models.ge import GeObjective, GeProgram, GeProject, GeProjectMember, GeTask
from app.services.ge_access import _governed_program_ids_for_user


@dataclass(frozen=True)
class PersonalTreeSets:
    """Ids retained in the actor's personal projection."""

    objective_ids: frozenset[str]
    program_ids: frozenset[str]


def _objective_parent_map(db: Session) -> dict[str, str | None]:
    rows = db.query(GeObjective.id, GeObjective.parent_id).all()
    return {oid: parent_id for oid, parent_id in rows}


def _program_objective_map(db: Session) -> dict[str, str]:
    rows = db.query(GeProgram.id, GeProgram.objective_id).all()
    return {pid: oid for pid, oid in rows}


def _children_by_parent(db: Session) -> dict[str | None, list[str]]:
    rows = db.query(GeObjective.id, GeObjective.parent_id).all()
    children: dict[str | None, list[str]] = {}
    for oid, parent_id in rows:
        children.setdefault(parent_id, []).append(oid)
    return children


def _governed_objective_ids(db: Session, user_id: str) -> set[str]:
    """Objective ids in the actor's governed subtree (owner/pmbp chain + descendants)."""
    uid = str(user_id).strip()
    if not uid:
        return set()

    objectives = db.query(
        GeObjective.id, GeObjective.parent_id, GeObjective.owner_user_id, GeObjective.pmbp_user_id
    ).all()
    children_by_parent: dict[str | None, list[str]] = {}
    owned: set[str] = set()
    for obj_id, parent_id, owner, pmbp in objectives:
        children_by_parent.setdefault(parent_id, []).append(obj_id)
        if (owner and str(owner).strip() == uid) or (pmbp and str(pmbp).strip() == uid):
            owned.add(obj_id)

    governed = set(owned)
    queue = list(owned)
    while queue:
        current = queue.pop()
        for child_id in children_by_parent.get(current, []):
            if child_id not in governed:
                governed.add(child_id)
                queue.append(child_id)

    # T3/C3: program owner/pmbp must NOT lift the parent objective into
    # governed — that would pull sibling programs into full subtree (C20
    # applies only to true objective governors). Owned programs enter via
    # _governed_program_ids_for_user; ancestors are skeleton-only.
    return governed


def _execution_anchor_program_and_project_ids(
    db: Session, user_id: str
) -> tuple[set[str], set[str]]:
    """Programs/projects where user is PM ∪ roster ∪ assignee (not created_by)."""
    uid = str(user_id).strip()
    if not uid:
        return set(), set()

    projects = (
        db.query(GeProject.id, GeProject.program_id, GeProject.pm_user_id)
        .filter(GeProject.deleted_at.is_(None))
        .all()
    )
    if not projects:
        return set(), set()

    project_ids = [p[0] for p in projects]
    member_rows = (
        db.query(GeProjectMember.project_id)
        .filter(GeProjectMember.user_id == uid, GeProjectMember.project_id.in_(project_ids))
        .all()
    )
    assignee_rows = (
        db.query(GeTask.project_id)
        .filter(GeTask.assignee_user_id == uid, GeTask.project_id.in_(project_ids))
        .distinct()
        .all()
    )
    anchor_project_ids = {row[0] for row in member_rows} | {row[0] for row in assignee_rows}
    for pid, program_id, pm_user_id in projects:
        if pm_user_id == uid:
            anchor_project_ids.add(pid)

    program_ids = {program_id for pid, program_id, _ in projects if pid in anchor_project_ids}
    return program_ids, anchor_project_ids


def _ancestor_objective_ids(obj_id: str, parent_by_id: dict[str, str | None]) -> set[str]:
    out: set[str] = set()
    current: str | None = obj_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        out.add(current)
        current = parent_by_id.get(current)
    return out


def compute_personal_tree_sets(db: Session, user: AuthUser) -> PersonalTreeSets:
    """Return objective/program id sets for the actor's personal projection."""
    if user.is_reviewer:
        all_obj = {row[0] for row in db.query(GeObjective.id).all()}
        all_prog = {row[0] for row in db.query(GeProgram.id).all()}
        return PersonalTreeSets(objective_ids=frozenset(all_obj), program_ids=frozenset(all_prog))

    uid = user.user_id
    parent_by_id = _objective_parent_map(db)
    prog_to_obj = _program_objective_map(db)

    governed_obj_ids = _governed_objective_ids(db, uid)
    governed_prog_ids = _governed_program_ids_for_user(db, uid)

    # C20: empty governed programs stay (already in governed_prog_ids).
    anchor_prog_ids, _ = _execution_anchor_program_and_project_ids(db, uid)

    keep_obj: set[str] = set(governed_obj_ids)
    keep_prog: set[str] = set(governed_prog_ids)

    for prog_id in governed_prog_ids | anchor_prog_ids:
        keep_prog.add(prog_id)
        obj_id = prog_to_obj.get(prog_id)
        if obj_id:
            keep_obj |= _ancestor_objective_ids(obj_id, parent_by_id)

    for obj_id in list(governed_obj_ids):
        keep_obj |= _ancestor_objective_ids(obj_id, parent_by_id)

    # Programs under governed objectives (full subtree) — includes empty (C20).
    for prog_id, obj_id in prog_to_obj.items():
        if obj_id in governed_obj_ids:
            keep_prog.add(prog_id)

    return PersonalTreeSets(
        objective_ids=frozenset(keep_obj),
        program_ids=frozenset(keep_prog),
    )


def program_ids_in_projection(db: Session, user: AuthUser) -> frozenset[str]:
    return compute_personal_tree_sets(db, user).program_ids


def objective_ids_in_projection(db: Session, user: AuthUser) -> frozenset[str]:
    return compute_personal_tree_sets(db, user).objective_ids


def objective_in_projection(db: Session, user: AuthUser, objective_id: str) -> bool:
    if user.is_reviewer:
        return True
    return objective_id in objective_ids_in_projection(db, user)


def program_in_projection(db: Session, user: AuthUser, program_id: str) -> bool:
    if user.is_reviewer:
        return True
    return program_id in program_ids_in_projection(db, user)


def subject_as_projection_user(subject_user_id: str) -> AuthUser:
    """Force non-reviewer projection for a subject (DESK-GE1 / G11).

    Never inherit caller reviewer flag — subject personal_tree ≠ full tree.
    """
    return AuthUser(
        user_id=str(subject_user_id or "").strip(),
        auth_method="service",
        is_reviewer=False,
    )


def _objective_spine_row(obj: GeObjective) -> dict[str, Any]:
    from app.services.ge_strategic import strategic_fields_out

    row: dict[str, Any] = {
        "id": obj.id,
        "name": obj.name,
        "level": obj.level,
        "owner_user_id": obj.owner_user_id,
        "pmbp_user_id": obj.pmbp_user_id,
        "is_default": bool(obj.is_default),
        "sort_order": obj.sort_order,
        **strategic_fields_out(obj),
    }
    if obj.parent_id:
        row["parent_id"] = obj.parent_id
    return row


def _program_spine_row(program: GeProgram) -> dict[str, Any]:
    from app.services.ge_strategic import strategic_fields_out

    return {
        "id": program.id,
        "name": program.name,
        "objective_id": program.objective_id,
        "owner_user_id": program.owner_user_id,
        "pmbp_user_id": program.pmbp_user_id,
        "is_default": bool(program.is_default),
        "sort_order": program.sort_order,
        **strategic_fields_out(program),
    }


def build_subject_personal_tree(
    db: Session,
    subject_user_id: str,
    *,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Flat personal_tree spine for subject (GE-VIS-1 · DESK-GE1 MS7a).

    Returns objectives/programs in projection with hang fields. Caller (BFF)
    rebuilds nest via parent_id / objective_id. Always non-reviewer geometry.
    """
    from app.services.ge_accountability import is_archived_entity
    from app.services.ge_strategic_lifecycle import refresh_lifecycle_entities

    uid = str(subject_user_id or "").strip()
    if not uid:
        return {"subject_user_id": "", "objectives": [], "programs": []}

    subject = subject_as_projection_user(uid)
    all_objectives = db.query(GeObjective).all()
    all_programs = db.query(GeProgram).all()
    refresh_lifecycle_entities(db, all_objectives, all_programs)

    projection = compute_personal_tree_sets(db, subject)
    keep_obj = projection.objective_ids
    keep_prog = projection.program_ids

    objectives_out: list[dict[str, Any]] = []
    for obj in all_objectives:
        if obj.id not in keep_obj:
            continue
        if obj.is_default:
            continue
        if not include_archived and is_archived_entity(obj):
            continue
        objectives_out.append(_objective_spine_row(obj))
    objectives_out.sort(key=lambda r: (int(r.get("sort_order") or 0), str(r.get("name") or "")))

    keep_obj_final = {r["id"] for r in objectives_out}
    programs_out: list[dict[str, Any]] = []
    for program in all_programs:
        if program.id not in keep_prog:
            continue
        if program.is_default:
            continue
        if not include_archived and is_archived_entity(program):
            continue
        if program.objective_id not in keep_obj_final:
            # Parent objective filtered out (e.g. archived) — drop program from spine.
            continue
        programs_out.append(_program_spine_row(program))
    programs_out.sort(key=lambda r: (int(r.get("sort_order") or 0), str(r.get("name") or "")))

    return {
        "subject_user_id": uid,
        "objectives": objectives_out,
        "programs": programs_out,
    }
