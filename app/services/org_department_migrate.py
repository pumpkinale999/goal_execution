"""Primary department migration (M31 · §4.1.5)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ge import GeObjective, GeProgram
from app.models.org import OrgDepartment


def department_has_primary_objectives(db: Session, department_id: str) -> bool:
    obj = (
        db.query(GeObjective.id)
        .filter(GeObjective.primary_department_id == department_id, GeObjective.is_default == 0)
        .first()
    )
    if obj is not None:
        return True
    prog = (
        db.query(GeProgram.id)
        .filter(GeProgram.primary_department_id == department_id, GeProgram.is_default == 0)
        .first()
    )
    return prog is not None


def migrate_primary_objectives(
    db: Session,
    source_department_id: str,
    target_department_id: str,
) -> dict[str, int]:
    source = db.get(OrgDepartment, source_department_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    target = db.get(OrgDepartment, target_department_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "target_not_found"})
    if source_department_id == target_department_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"detail": "same_department"})

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    objectives = (
        db.query(GeObjective)
        .filter(GeObjective.primary_department_id == source_department_id, GeObjective.is_default == 0)
        .all()
    )
    programs = (
        db.query(GeProgram)
        .filter(GeProgram.primary_department_id == source_department_id, GeProgram.is_default == 0)
        .all()
    )
    for obj in objectives:
        obj.primary_department_id = target_department_id
        obj.primary_department_needs_confirmation = False
        obj.updated_at = now
    for prog in programs:
        prog.primary_department_id = target_department_id
        prog.primary_department_needs_confirmation = False
        prog.updated_at = now
    db.commit()
    return {
        "objectives_migrated": len(objectives),
        "programs_migrated": len(programs),
    }
