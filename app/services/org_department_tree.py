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
