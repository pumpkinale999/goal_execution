"""Helpers for nested org departments."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.org import OrgDepartment


def department_has_children(db: Session, department_id: str) -> bool:
    return (
        db.query(OrgDepartment.id)
        .filter(OrgDepartment.parent_id == department_id)
        .limit(1)
        .first()
        is not None
    )


def department_is_ancestor(db: Session, ancestor_id: str, node_id: str) -> bool:
    """True when ancestor_id appears on the parent chain above node_id."""
    seen: set[str] = set()
    cur: str | None = node_id
    while cur and cur not in seen:
        if cur == ancestor_id:
            return True
        seen.add(cur)
        dept = db.get(OrgDepartment, cur)
        if dept is None:
            break
        cur = dept.parent_id
    return False
