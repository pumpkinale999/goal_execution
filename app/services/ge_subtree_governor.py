"""Sub-tree governor checks (§4.2.0.2 · P2)."""

from __future__ import annotations

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
        if _owner_matches(obj.owner_user_id, user_id):
            return True
        current_id = obj.parent_id
    return False


def is_subtree_governor(
    db: Session,
    *,
    user_id: str,
    objective_id: str | None = None,
    program_id: str | None = None,
    project_id: str | None = None,
) -> bool:
    """True when user owns this scope or an ancestor Objective/Program on the path."""
    uid = str(user_id).strip()
    if not uid:
        return False

    if project_id is not None:
        project = db.get(GeProject, str(project_id))
        if project is None or project.deleted_at is not None:
            return False
        return is_subtree_governor(db, user_id=uid, program_id=project.program_id)

    if program_id is not None:
        program = db.get(GeProgram, str(program_id))
        if program is None:
            return False
        if _owner_matches(program.owner_user_id, uid):
            return True
        return _objective_chain_governor(db, user_id=uid, objective_id=program.objective_id)

    if objective_id is not None:
        return _objective_chain_governor(db, user_id=uid, objective_id=str(objective_id))

    return False
