"""Strategic chain write operations (P2 · §4.2.0.1)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants import GE_DEFAULT_OBJECTIVE_ID, GE_DEFAULT_PROGRAM_ID, GE_DEFAULT_SUB_OBJECTIVE_ID
from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_bootstrap import ensure_ge_bootstrap
from app.services.ge_graph import now_iso


def _require_sub_objective(objective: GeObjective) -> None:
    if objective.level != "sub" or not objective.parent_id:
        raise HTTPException(status_code=400, detail={"detail": "program_requires_sub_objective"})


def create_objective(db: Session, body: dict[str, Any]) -> dict[str, Any]:
    ensure_ge_bootstrap(db)
    name = str(body.get("name") or "").strip()
    parent_id = body.get("parent_id")
    if not name:
        raise HTTPException(status_code=400, detail={"detail": "invalid_name"})
    if not parent_id:
        raise HTTPException(status_code=400, detail={"detail": "parent_id_required"})
    parent = db.get(GeObjective, str(parent_id))
    if parent is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    level = "sub" if parent.level == "company" else "sub"
    now = now_iso()
    obj = GeObjective(
        id=str(uuid.uuid4()),
        name=name,
        level=level,
        parent_id=str(parent_id),
        owner_user_id=body.get("owner_user_id"),
        is_default=0,
        created_at=now,
        updated_at=now,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _objective_out(obj)


def patch_objective(db: Session, objective_id: str, body: dict[str, Any]) -> dict[str, Any]:
    ensure_ge_bootstrap(db)
    obj = db.get(GeObjective, objective_id)
    if obj is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if body.get("name") is not None:
        name = str(body["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail={"detail": "invalid_name"})
        obj.name = name
    if "owner_user_id" in body:
        obj.owner_user_id = body.get("owner_user_id")
    obj.updated_at = now_iso()
    db.commit()
    db.refresh(obj)
    return _objective_out(obj)


def create_program(db: Session, body: dict[str, Any]) -> dict[str, Any]:
    ensure_ge_bootstrap(db)
    name = str(body.get("name") or "").strip()
    objective_id = body.get("objective_id")
    if not name:
        raise HTTPException(status_code=400, detail={"detail": "invalid_name"})
    if not objective_id:
        raise HTTPException(status_code=400, detail={"detail": "objective_id_required"})
    objective = db.get(GeObjective, str(objective_id))
    if objective is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    _require_sub_objective(objective)
    now = now_iso()
    program = GeProgram(
        id=str(uuid.uuid4()),
        name=name,
        objective_id=str(objective_id),
        owner_user_id=body.get("owner_user_id"),
        is_default=0,
        created_at=now,
        updated_at=now,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return _program_out(program)


def patch_program(db: Session, program_id: str, body: dict[str, Any]) -> dict[str, Any]:
    ensure_ge_bootstrap(db)
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if program.id == GE_DEFAULT_PROGRAM_ID:
        if body.get("objective_id") is not None and str(body["objective_id"]) != program.objective_id:
            raise HTTPException(status_code=403, detail={"detail": "default_immutable"})
    if body.get("name") is not None:
        name = str(body["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail={"detail": "invalid_name"})
        program.name = name
    if body.get("objective_id") is not None:
        objective_id = str(body["objective_id"])
        objective = db.get(GeObjective, objective_id)
        if objective is None:
            raise HTTPException(status_code=404, detail={"detail": "not_found"})
        _require_sub_objective(objective)
        program.objective_id = objective_id
    if "owner_user_id" in body:
        program.owner_user_id = body.get("owner_user_id")
    program.updated_at = now_iso()
    db.commit()
    db.refresh(program)
    return _program_out(program)


def delete_objective(db: Session, objective_id: str) -> None:
    ensure_ge_bootstrap(db)
    obj = db.get(GeObjective, objective_id)
    if obj is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if obj.is_default or objective_id in (
        GE_DEFAULT_OBJECTIVE_ID,
        GE_DEFAULT_SUB_OBJECTIVE_ID,
    ):
        raise HTTPException(status_code=403, detail={"detail": "default_immutable"})
    child = db.query(GeObjective).filter(GeObjective.parent_id == objective_id).first()
    if child is not None:
        raise HTTPException(status_code=409, detail={"detail": "objective_not_empty"})
    program = db.query(GeProgram).filter(GeProgram.objective_id == objective_id).first()
    if program is not None:
        raise HTTPException(status_code=409, detail={"detail": "objective_not_empty"})
    db.delete(obj)
    db.commit()


def delete_program(db: Session, program_id: str) -> None:
    ensure_ge_bootstrap(db)
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if program.is_default or program_id == GE_DEFAULT_PROGRAM_ID:
        raise HTTPException(status_code=403, detail={"detail": "default_immutable"})
    project = db.query(GeProject).filter(GeProject.program_id == program_id).first()
    if project is not None:
        raise HTTPException(status_code=409, detail={"detail": "program_not_empty"})
    db.delete(program)
    db.commit()


def _objective_out(obj: GeObjective) -> dict[str, Any]:
    return {
        "id": obj.id,
        "name": obj.name,
        "level": obj.level,
        "parent_id": obj.parent_id,
        "owner_user_id": obj.owner_user_id,
        "is_default": bool(obj.is_default),
    }


def _program_out(program: GeProgram) -> dict[str, Any]:
    return {
        "id": program.id,
        "name": program.name,
        "objective_id": program.objective_id,
        "owner_user_id": program.owner_user_id,
        "is_default": bool(program.is_default),
    }
