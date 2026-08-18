"""Goal-tree subtree governor checks (GE-AUTHZ-API · is_goal_subtree_governor).

M41: governor = owner chain ∪ effective PMBP chain. Accountability remains owner-only
(`is_goal_direct_owner`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.ge import GeObjective, GeProgram, GeProject


def _owner_matches(owner_user_id: str | None, user_id: str) -> bool:
    if not owner_user_id or not str(owner_user_id).strip():
        return False
    return str(owner_user_id).strip() == user_id


def _objective_chain_governor(db: Session, *, user_id: str, objective_id: str) -> bool:
    current_id: str | None = objective_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        obj = db.get(GeObjective, current_id)
        if obj is None:
            return False
        if _owner_matches(obj.owner_user_id, user_id) or _owner_matches(obj.pmbp_user_id, user_id):
            return True
        current_id = obj.parent_id
    return False


def is_goal_direct_owner(
    db: Session,
    *,
    user_id: str,
    objective_id: str | None = None,
    program_id: str | None = None,
) -> bool:
    """True only when this node's owner_user_id equals user (no ancestors, no PMBP)."""
    uid = str(user_id).strip()
    if not uid:
        return False
    if program_id is not None:
        program = db.get(GeProgram, str(program_id))
        if program is None:
            return False
        return _owner_matches(program.owner_user_id, uid)
    if objective_id is not None:
        obj = db.get(GeObjective, str(objective_id))
        if obj is None:
            return False
        return _owner_matches(obj.owner_user_id, uid)
    return False


def can_appoint_pmbp(
    db: Session,
    *,
    user_id: str,
    is_reviewer: bool = False,
    objective_id: str | None = None,
    program_id: str | None = None,
) -> bool:
    """Direct owner ∨ ancestor owner ∨ reviewer. Effective PMBP alone is not enough."""
    if is_reviewer:
        return True
    uid = str(user_id).strip()
    if not uid:
        return False
    if program_id is not None:
        program = db.get(GeProgram, str(program_id))
        if program is None:
            return False
        if _owner_matches(program.owner_user_id, uid):
            return True
        return can_appoint_pmbp(db, user_id=uid, objective_id=program.objective_id)
    if objective_id is not None:
        current_id: str | None = str(objective_id)
        seen: set[str] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            obj = db.get(GeObjective, current_id)
            if obj is None:
                return False
            if _owner_matches(obj.owner_user_id, uid):
                return True
            current_id = obj.parent_id
    return False


def _inherited_from_payload(kind: str, node: GeObjective | GeProgram) -> dict[str, Any]:
    return {"kind": kind, "id": node.id, "name": node.name}


def effective_pmbp_for_objective(
    db: Session, obj: GeObjective
) -> tuple[str | None, dict[str, Any] | None]:
    if obj.pmbp_user_id and str(obj.pmbp_user_id).strip():
        return str(obj.pmbp_user_id).strip(), None
    current_id = obj.parent_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        parent = db.get(GeObjective, current_id)
        if parent is None:
            break
        if parent.pmbp_user_id and str(parent.pmbp_user_id).strip():
            return str(parent.pmbp_user_id).strip(), _inherited_from_payload("objective", parent)
        current_id = parent.parent_id
    return None, None


def effective_pmbp_for_program(
    db: Session, program: GeProgram
) -> tuple[str | None, dict[str, Any] | None]:
    if program.pmbp_user_id and str(program.pmbp_user_id).strip():
        return str(program.pmbp_user_id).strip(), None
    objective = db.get(GeObjective, program.objective_id)
    if objective is None:
        return None, None
    eid, inherited = effective_pmbp_for_objective(db, objective)
    if not eid:
        return None, None
    if inherited is None:
        return eid, _inherited_from_payload("objective", objective)
    return eid, inherited


def attach_effective_pmbp(data: dict[str, Any], eid: str | None, inherited: dict[str, Any] | None) -> dict[str, Any]:
    data["effective_pmbp_user_id"] = eid
    if inherited is not None:
        data["effective_pmbp_inherited_from"] = inherited
    return data


def is_goal_subtree_governor(
    db: Session,
    *,
    user_id: str,
    objective_id: str | None = None,
    program_id: str | None = None,
    project_id: str | None = None,
) -> bool:
    """True when user owns this scope or an ancestor Objective/Program on the path,
    or is effective PMBP on that path.

    Does **not** consider is_reviewer or PM — callers OR those separately.
    """
    uid = str(user_id).strip()
    if not uid:
        return False

    if project_id is not None:
        project = db.get(GeProject, str(project_id))
        if project is None or project.deleted_at is not None:
            return False
        return is_goal_subtree_governor(db, user_id=uid, program_id=project.program_id)

    if program_id is not None:
        program = db.get(GeProgram, str(program_id))
        if program is None:
            return False
        if _owner_matches(program.owner_user_id, uid) or _owner_matches(program.pmbp_user_id, uid):
            return True
        return _objective_chain_governor(db, user_id=uid, objective_id=program.objective_id)

    if objective_id is not None:
        return _objective_chain_governor(db, user_id=uid, objective_id=str(objective_id))

    return False
