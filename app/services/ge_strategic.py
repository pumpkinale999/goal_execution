"""Strategic chain write operations (P2 + M29 · §4.2.0.1 / §4.2.0.4)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants import (
    SAMPLE_PHASE_NAME,
    SAMPLE_PROGRAM_NAME,
    SAMPLE_PROJECT_NAME,
    SAMPLE_SUB_OBJECTIVE_NAME,
)
from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_graph import now_iso, record_audit
from app.services.ge_project_create import create_project
from app.services.ge_sort_order import (
    next_objective_sort_order,
    next_program_sort_order,
    sibling_objectives,
    sibling_programs,
)
from app.services.ge_strategic_lifecycle import invalidate_lifecycle_refresh
from app.services.ge_strategic_period import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_ARCHIVED,
    LIFECYCLE_PENDING,
    LOCKED_LIFECYCLES,
    TERMINAL_LIFECYCLES,
    company_ancestor_bounds,
    default_sub_period,
    period_within_bounds,
    planning_year_from_start,
    validate_company_period,
    validate_sub_objective_period,
    validate_sub_program_period,
    year_bounds,
)


def _require_sub_objective(objective: GeObjective) -> None:
    if objective.level != "sub" or not objective.parent_id:
        raise HTTPException(status_code=400, detail={"detail": "program_requires_sub_objective"})


def _require_owner(body: dict[str, Any]) -> str:
    owner = body.get("owner_user_id")
    if owner is None or not str(owner).strip():
        raise HTTPException(status_code=400, detail={"detail": "owner_required"})
    return str(owner).strip()


def _is_lifecycle_locked(entity: GeObjective | GeProgram) -> bool:
    status = entity.lifecycle_status or LIFECYCLE_ACTIVE
    return status in LOCKED_LIFECYCLES


# When lifecycle is locked (pending_assessment / terminal), still allow accountability edits.
# Strategic fields (period / department / reparent) remain forbidden.
_ACCOUNTABILITY_PATCH_KEYS = frozenset({"name", "owner_user_id"})


def _assert_patch_allowed(entity: GeObjective | GeProgram, body: dict[str, Any]) -> None:
    if not _is_lifecycle_locked(entity):
        return
    keys = {k for k in body.keys() if k != "lifecycle_status"}
    if keys and keys.issubset(_ACCOUNTABILITY_PATCH_KEYS):
        return
    raise HTTPException(status_code=409, detail={"detail": "objective_locked"})


def _validate_department(db: Session, department_id: str | None) -> None:
    """Org authority is skstudio; GE only stores primary_department_id as opaque id."""
    del db  # kept for call-site compatibility
    if not department_id:
        raise HTTPException(status_code=400, detail={"detail": "primary_department_required"})


def _apply_objective_period(
    db: Session,
    obj: GeObjective,
    body: dict[str, Any],
    *,
    parent: GeObjective,
    is_create: bool,
) -> None:
    gran = body.get("period_granularity")
    start = body.get("period_start")
    end = body.get("period_end")
    if is_create and obj.level == "sub" and not start:
        gran, start, end = default_sub_period()
    if gran is not None:
        obj.period_granularity = str(gran)
    if start is not None:
        obj.period_start = str(start)
    if end is not None:
        obj.period_end = str(end)
    if obj.period_granularity and obj.period_start and obj.period_end:
        if obj.level == "company":
            validate_company_period(obj.period_granularity, obj.period_start, obj.period_end)
        elif obj.level == "sub":
            validate_sub_objective_period(obj.period_granularity, obj.period_start, obj.period_end)
            bounds = company_ancestor_bounds(db, obj) or company_ancestor_bounds(db, parent)
            if bounds and not period_within_bounds(obj.period_start, obj.period_end, bounds[0], bounds[1]):
                raise HTTPException(
                    status_code=400,
                    detail={"detail": "period_out_of_parent_bounds"},
                )


def _apply_program_period(
    db: Session,
    program: GeProgram,
    body: dict[str, Any],
    *,
    objective: GeObjective,
    is_create: bool,
) -> None:
    gran = body.get("period_granularity")
    start = body.get("period_start")
    end = body.get("period_end")
    if is_create and not start and objective.period_start and objective.period_end:
        if objective.period_granularity == "year":
            gran, start, end = default_sub_period()
        else:
            gran = objective.period_granularity
            start = objective.period_start
            end = objective.period_end
    if gran is not None:
        program.period_granularity = str(gran)
    if start is not None:
        program.period_start = str(start)
    if end is not None:
        program.period_end = str(end)
    if program.period_granularity and program.period_start and program.period_end:
        validate_sub_program_period(
            program.period_granularity,
            program.period_start,
            program.period_end,
        )
        bounds = company_ancestor_bounds(db, objective)
        if bounds and not period_within_bounds(
            program.period_start, program.period_end, bounds[0], bounds[1]
        ):
            raise HTTPException(
                status_code=400,
                detail={"detail": "period_out_of_parent_bounds"},
            )


def create_objective(db: Session, body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("name") or "").strip()
    parent_id = body.get("parent_id")
    if not name:
        raise HTTPException(status_code=400, detail={"detail": "invalid_name"})
    if not parent_id:
        raise HTTPException(status_code=400, detail={"detail": "parent_id_required"})
    parent = db.get(GeObjective, str(parent_id))
    if parent is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    level = "sub"
    now = now_iso()
    owner_user_id = _require_owner(body)
    obj = GeObjective(
        id=str(uuid.uuid4()),
        name=name,
        level=level,
        parent_id=str(parent_id),
        owner_user_id=owner_user_id,
        is_default=0,
        lifecycle_status=LIFECYCLE_ACTIVE,
        primary_department_needs_confirmation=0,
        created_at=now,
        updated_at=now,
    )
    dept = body.get("primary_department_id")
    _validate_department(db, str(dept) if dept else None)
    obj.primary_department_id = str(dept) if dept else None
    _apply_objective_period(db, obj, body, parent=parent, is_create=True)
    obj.sort_order = next_objective_sort_order(db, str(parent_id))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    invalidate_lifecycle_refresh()
    return objective_out(obj)


def patch_objective(db: Session, objective_id: str, body: dict[str, Any]) -> dict[str, Any]:
    obj = db.get(GeObjective, objective_id)
    if obj is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if body.get("lifecycle_status") is not None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    _assert_patch_allowed(obj, body)
    if body.get("name") is not None:
        name = str(body["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail={"detail": "invalid_name"})
        if (
            obj.level == "company"
            and not obj.is_default
            and obj.period_start
            and len(obj.period_start) >= 4
        ):
            try:
                year = int(obj.period_start[:4])
            except ValueError:
                year = None
            if year is not None:
                if len(name) > 200:
                    raise HTTPException(status_code=400, detail={"detail": "name_invalid"})
                _assert_annual_name_unique(db, year=year, name=name, exclude_id=obj.id)
        obj.name = name
    if "owner_user_id" in body:
        obj.owner_user_id = body.get("owner_user_id")
    if "primary_department_id" in body and obj.level == "sub":
        dept = body.get("primary_department_id")
        if dept:
            _validate_department(db, str(dept))
            obj.primary_department_id = str(dept)
            obj.primary_department_needs_confirmation = 0
    parent = db.get(GeObjective, obj.parent_id) if obj.parent_id else None
    if parent is not None and not _is_lifecycle_locked(obj):
        _apply_objective_period(db, obj, body, parent=parent, is_create=False)
    obj.updated_at = now_iso()
    db.commit()
    db.refresh(obj)
    invalidate_lifecycle_refresh()
    return objective_out(obj)


def create_program(db: Session, body: dict[str, Any]) -> dict[str, Any]:
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
    owner_user_id = _require_owner(body)
    program = GeProgram(
        id=str(uuid.uuid4()),
        name=name,
        objective_id=str(objective_id),
        owner_user_id=owner_user_id,
        is_default=0,
        lifecycle_status=LIFECYCLE_ACTIVE,
        primary_department_needs_confirmation=0,
        created_at=now,
        updated_at=now,
    )
    dept = body.get("primary_department_id")
    if not dept and objective.primary_department_id:
        dept = objective.primary_department_id
    _validate_department(db, str(dept) if dept else None)
    program.primary_department_id = str(dept) if dept else None
    _apply_program_period(db, program, body, objective=objective, is_create=True)
    program.sort_order = next_program_sort_order(db, str(objective_id))
    db.add(program)
    db.commit()
    db.refresh(program)
    invalidate_lifecycle_refresh()
    return program_out(program, db)


def patch_program(db: Session, program_id: str, body: dict[str, Any]) -> dict[str, Any]:
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if body.get("lifecycle_status") is not None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    _assert_patch_allowed(program, body)
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
    if "primary_department_id" in body:
        dept = body.get("primary_department_id")
        if dept:
            _validate_department(db, str(dept))
            program.primary_department_id = str(dept)
            program.primary_department_needs_confirmation = 0
    objective = db.get(GeObjective, program.objective_id)
    if objective is not None and not _is_lifecycle_locked(program):
        _apply_program_period(db, program, body, objective=objective, is_create=False)
    program.updated_at = now_iso()
    db.commit()
    db.refresh(program)
    invalidate_lifecycle_refresh()
    return program_out(program, db)


def _normalize_annual_name(raw: Any) -> str:
    name = str(raw or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail={"detail": "name_required"})
    if len(name) > 200:
        raise HTTPException(status_code=400, detail={"detail": "name_invalid"})
    return name


def _formal_company_roots_for_year(db: Session, year: int) -> list[GeObjective]:
    start, _ = year_bounds(year)
    return (
        db.query(GeObjective)
        .filter(
            GeObjective.level == "company",
            GeObjective.is_default == 0,
            GeObjective.period_start == start,
        )
        .all()
    )


def _assert_annual_name_unique(
    db: Session, *, year: int, name: str, exclude_id: str | None = None
) -> None:
    for root in _formal_company_roots_for_year(db, year):
        if exclude_id and root.id == exclude_id:
            continue
        if (root.name or "") == name:
            raise HTTPException(status_code=400, detail={"detail": "duplicate_annual_name"})


def create_objective_year(db: Session, body: dict[str, Any], *, actor_user_id: str) -> dict[str, Any]:
    planning_year = body.get("planning_year")
    if planning_year is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    year = int(planning_year)
    if body.get("copy_from_year") is not None:
        raise HTTPException(status_code=400, detail={"detail": "copy_from_year_deprecated"})
    name = _normalize_annual_name(body.get("name"))
    start, end = year_bounds(year)

    existing = _formal_company_roots_for_year(db, year)
    if len(existing) >= 10:
        raise HTTPException(status_code=400, detail={"detail": "annual_root_limit_exceeded"})
    _assert_annual_name_unique(db, year=year, name=name)

    copy_from_id = body.get("copy_from_objective_id")
    now = now_iso()
    raw_owner = body.get("owner_user_id")
    owner_user_id = (
        str(raw_owner).strip()
        if raw_owner is not None and str(raw_owner).strip()
        else str(actor_user_id)
    )

    company = GeObjective(
        id=str(uuid.uuid4()),
        name=name,
        level="company",
        parent_id=None,
        owner_user_id=owner_user_id,
        is_default=0,
        period_granularity="year",
        period_start=start,
        period_end=end,
        lifecycle_status=LIFECYCLE_ACTIVE,
        primary_department_needs_confirmation=0,
        sort_order=(
            max((root.sort_order for root in existing), default=0) + 10 if existing else 10
        ),
        created_at=now,
        updated_at=now,
    )
    db.add(company)
    db.flush()

    if copy_from_id is not None:
        _copy_year_structure_from_objective(db, company, str(copy_from_id), now=now)

    if body.get("include_sample_structure"):
        _append_sample_structure(db, company, actor_user_id=actor_user_id, now=now)

    record_audit(
        db,
        actor_user_id=actor_user_id,
        entity_type="objective",
        entity_id=company.id,
        action="create_objective_year",
        payload={
            "planning_year": year,
            "name": name,
            "owner_user_id": owner_user_id,
            "copy_from_objective_id": copy_from_id,
            "include_sample_structure": bool(body.get("include_sample_structure")),
        },
    )
    db.commit()
    db.refresh(company)
    invalidate_lifecycle_refresh()
    return objective_out(company)


def _append_sample_structure(
    db: Session, company: GeObjective, *, actor_user_id: str, now: str
) -> None:
    owner = str(actor_user_id)
    # Org tables no longer live in GE; sample structure leaves dept for user to set in UI.
    sub_gran, sub_start, sub_end = default_sub_period()
    sub = GeObjective(
        id=str(uuid.uuid4()),
        name=SAMPLE_SUB_OBJECTIVE_NAME,
        level="sub",
        parent_id=company.id,
        owner_user_id=owner,
        is_default=0,
        period_granularity=sub_gran,
        period_start=sub_start,
        period_end=sub_end,
        lifecycle_status=LIFECYCLE_ACTIVE,
        primary_department_id=None,
        primary_department_needs_confirmation=1,
        sort_order=next_objective_sort_order(db, company.id),
        created_at=now,
        updated_at=now,
    )
    db.add(sub)
    db.flush()

    gran, prog_start, prog_end = default_sub_period()
    program = GeProgram(
        id=str(uuid.uuid4()),
        name=SAMPLE_PROGRAM_NAME,
        objective_id=sub.id,
        owner_user_id=owner,
        is_default=0,
        period_granularity=gran,
        period_start=prog_start,
        period_end=prog_end,
        lifecycle_status=LIFECYCLE_ACTIVE,
        primary_department_id=sub.primary_department_id,
        primary_department_needs_confirmation=1,
        sort_order=next_program_sort_order(db, sub.id),
        created_at=now,
        updated_at=now,
    )
    db.add(program)
    db.flush()

    create_project(
        db,
        actor_user_id=owner,
        body={
            "name": SAMPLE_PROJECT_NAME,
            "pm_user_id": owner,
            "program_id": program.id,
            "phases": [
                {
                    "sequence": 1,
                    "name": SAMPLE_PHASE_NAME,
                    "gate_items": [],
                    "tasks": [],
                }
            ],
        },
        commit=False,
    )


def _copy_year_structure_from_objective(
    db: Session,
    target_company: GeObjective,
    source_objective_id: str,
    *,
    now: str,
) -> None:
    source = db.get(GeObjective, source_objective_id)
    if (
        source is None
        or source.level != "company"
        or bool(source.is_default)
    ):
        raise HTTPException(status_code=400, detail={"detail": "copy_source_invalid"})
    subs = sibling_objectives(db, source.id)
    for sub in subs:
        if sub.is_default:
            continue
        new_sub = GeObjective(
            id=str(uuid.uuid4()),
            name=sub.name,
            level="sub",
            parent_id=target_company.id,
            owner_user_id=sub.owner_user_id,
            is_default=0,
            period_granularity=sub.period_granularity,
            period_start=sub.period_start,
            period_end=sub.period_end,
            lifecycle_status=LIFECYCLE_ACTIVE,
            primary_department_id=sub.primary_department_id,
            primary_department_needs_confirmation=sub.primary_department_needs_confirmation,
            sort_order=sub.sort_order,
            created_at=now,
            updated_at=now,
        )
        db.add(new_sub)
        db.flush()
        for prog in sibling_programs(db, sub.id):
            if prog.is_default:
                continue
            db.add(
                GeProgram(
                    id=str(uuid.uuid4()),
                    name=prog.name,
                    objective_id=new_sub.id,
                    owner_user_id=prog.owner_user_id,
                    is_default=0,
                    period_granularity=prog.period_granularity,
                    period_start=prog.period_start,
                    period_end=prog.period_end,
                    lifecycle_status=LIFECYCLE_ACTIVE,
                    primary_department_id=prog.primary_department_id,
                    primary_department_needs_confirmation=prog.primary_department_needs_confirmation,
                    sort_order=prog.sort_order,
                    created_at=now,
                    updated_at=now,
                )
            )


def assess_objective(
    db: Session,
    objective_id: str,
    body: dict[str, Any],
    *,
    actor_user_id: str,
) -> dict[str, Any]:
    obj = db.get(GeObjective, objective_id)
    if obj is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if obj.is_default:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    if obj.lifecycle_status != LIFECYCLE_PENDING:
        raise HTTPException(status_code=400, detail={"detail": "not_pending_assessment"})
    outcome = body.get("outcome")
    if outcome not in ("met", "partial_met", "not_met"):
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    obj.lifecycle_status = str(outcome)
    obj.updated_at = now_iso()
    record_audit(
        db,
        actor_user_id=actor_user_id,
        entity_type="objective",
        entity_id=obj.id,
        action="assess_objective",
        payload={"outcome": outcome, "note": body.get("note"), "final_status": outcome},
    )
    db.commit()
    db.refresh(obj)
    invalidate_lifecycle_refresh()
    return objective_out(obj)


def assess_program(
    db: Session,
    program_id: str,
    body: dict[str, Any],
    *,
    actor_user_id: str,
) -> dict[str, Any]:
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    if program.is_default:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    if program.lifecycle_status != LIFECYCLE_PENDING:
        raise HTTPException(status_code=400, detail={"detail": "not_pending_assessment"})
    outcome = body.get("outcome")
    if outcome not in ("met", "partial_met", "not_met"):
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    program.lifecycle_status = str(outcome)
    program.updated_at = now_iso()
    record_audit(
        db,
        actor_user_id=actor_user_id,
        entity_type="program",
        entity_id=program.id,
        action="assess_program",
        payload={"outcome": outcome, "note": body.get("note"), "final_status": outcome},
    )
    db.commit()
    db.refresh(program)
    invalidate_lifecycle_refresh()
    return program_out(program, db)


def delete_objective(db: Session, objective_id: str) -> None:
    obj = db.get(GeObjective, objective_id)
    if obj is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    child = db.query(GeObjective).filter(GeObjective.parent_id == objective_id).first()
    if child is not None:
        raise HTTPException(status_code=409, detail={"detail": "objective_not_empty"})
    program = db.query(GeProgram).filter(GeProgram.objective_id == objective_id).first()
    if program is not None:
        raise HTTPException(status_code=409, detail={"detail": "objective_not_empty"})
    db.delete(obj)
    db.commit()
    invalidate_lifecycle_refresh()


def delete_program(db: Session, program_id: str) -> None:
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    active = (
        db.query(GeProject)
        .filter(GeProject.program_id == program_id, GeProject.deleted_at.is_(None))
        .first()
    )
    if active is not None:
        raise HTTPException(status_code=409, detail={"detail": "program_not_empty"})
    db.delete(program)
    db.commit()
    invalidate_lifecycle_refresh()


def strategic_fields_out(entity: GeObjective | GeProgram) -> dict[str, Any]:
    data: dict[str, Any] = {
        "period_granularity": entity.period_granularity,
        "period_start": entity.period_start,
        "period_end": entity.period_end,
        "lifecycle_status": entity.lifecycle_status or LIFECYCLE_ACTIVE,
        "primary_department_id": entity.primary_department_id,
        "primary_department_needs_confirmation": bool(
            entity.primary_department_needs_confirmation
        ),
    }
    if isinstance(entity, GeObjective) and entity.level == "company" and not entity.is_default:
        py = planning_year_from_start(entity.period_start)
        if py is not None:
            data["planning_year"] = py
    return data


def objective_out(obj: GeObjective) -> dict[str, Any]:
    return {
        "id": obj.id,
        "name": obj.name,
        "level": obj.level,
        "parent_id": obj.parent_id,
        "owner_user_id": obj.owner_user_id,
        "is_default": bool(obj.is_default),
        "sort_order": obj.sort_order,
        **strategic_fields_out(obj),
    }


def program_out(program: GeProgram, db: Session | None = None) -> dict[str, Any]:
    from app.services.ge_schedule_derive import build_program_period

    objective = None
    if db is not None:
        objective = program.objective if program.objective is not None else db.get(GeObjective, program.objective_id)
    resolved = build_program_period(program, objective=objective)
    data: dict[str, Any] = {
        "id": program.id,
        "name": program.name,
        "objective_id": program.objective_id,
        "owner_user_id": program.owner_user_id,
        "is_default": bool(program.is_default),
        "sort_order": program.sort_order,
        **strategic_fields_out(program),
    }
    if resolved:
        data["resolved_period_start"] = resolved["period_start"]
        data["resolved_period_end"] = resolved["period_end"]
        data["resolved_period_granularity"] = resolved.get("period_granularity")
        data["period_is_inherited"] = not (program.period_start and program.period_end)
    else:
        data["period_is_inherited"] = False
    return data
