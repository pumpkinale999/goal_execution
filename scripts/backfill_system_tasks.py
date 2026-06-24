#!/usr/bin/env python3
"""Backfill system lifecycle tasks/gate items for legacy GE projects (M20).

Usage (from goal_execution repo root)::

    python scripts/backfill_system_tasks.py --dry-run
    python scripts/backfill_system_tasks.py --project-name "东城中药"

Ensures built-in Start/End task + gate item exist even when the phase already
has other business content. Idempotent: skips sides that already have system entities.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import HTTPException

from app.constants import SYSTEM_END_PHASE_NAME
from app.db import init_db, session_scope
from app.models.ge import GeGate, GePhase, GeProject
from app.services.ge_graph import now_iso, recompute_gate_and_phases, recompute_task_status
from app.services.ge_graph_validate import validate_project_graph_db
from app.services.ge_system_tasks import (
    needs_system_end_seed,
    needs_system_end_sign_route_seed,
    needs_system_start_seed,
    seed_system_lifecycle_graph,
)


def _find_system_phases(db, project_id: str) -> tuple[GePhase | None, GeGate | None, GePhase | None, GeGate | None]:
    phases = (
        db.query(GePhase)
        .filter(GePhase.project_id == project_id)
        .order_by(GePhase.sequence)
        .all()
    )
    start_phase = next((p for p in phases if p.is_system and p.sequence == 0), None)
    end_phase = next((p for p in phases if p.is_system and p.name == SYSTEM_END_PHASE_NAME), None)
    start_gate = (
        db.query(GeGate).filter(GeGate.phase_id == start_phase.id).first() if start_phase else None
    )
    end_gate = db.query(GeGate).filter(GeGate.phase_id == end_phase.id).first() if end_phase else None
    return start_phase, start_gate, end_phase, end_gate


def backfill_project(db, project: GeProject, *, dry_run: bool) -> str:
    start_phase, start_gate, end_phase, end_gate = _find_system_phases(db, project.id)
    if start_phase is None or start_gate is None or end_phase is None or end_gate is None:
        return "skip:missing_system_phases"

    seed_start = needs_system_start_seed(db, start_phase.id)
    seed_end = needs_system_end_seed(db, end_phase.id)
    seed_end_sign_route = needs_system_end_sign_route_seed(db, end_phase.id)
    if not seed_start and not seed_end and not seed_end_sign_route:
        return "skip:system_entities_present"

    if dry_run:
        parts = []
        if seed_start:
            parts.append("start")
        if seed_end:
            parts.append("end")
        if seed_end_sign_route and not seed_end:
            parts.append("end_sign_route")
        return f"dry-run:would_seed_{'+'.join(parts)}"

    now = now_iso()
    legacy_start_complete = start_phase.status == "completed"
    seed_system_lifecycle_graph(
        db,
        project_id=project.id,
        pm_user_id=project.pm_user_id,
        start_phase_id=start_phase.id,
        start_gate_id=start_gate.id,
        end_phase_id=end_phase.id,
        end_gate_id=end_gate.id,
        now=now,
        start_phase_planned_end=start_phase.planned_end,
        end_phase_planned_end=end_phase.planned_end,
        seed_start=seed_start,
        seed_end=seed_end,
        seed_end_sign_route=seed_end_sign_route,
        legacy_start_complete=legacy_start_complete,
    )
    try:
        validate_project_graph_db(db, project.id)
    except HTTPException as exc:
        detail = exc.detail.get("detail") if isinstance(exc.detail, dict) else exc.detail
        print(f"warn:validate_failed detail={detail!r} project={project.name!r}")
    recompute_gate_and_phases(db, project.id)
    recompute_task_status(db, project.id)
    project.updated_at = now
    return f"ok:seeded_start={seed_start},end={seed_end},end_sign_route={seed_end_sign_route},legacy_start_complete={legacy_start_complete}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill system lifecycle tasks for GE projects")
    parser.add_argument("--project-id", help="Only backfill this project id")
    parser.add_argument("--project-name", help="Only backfill projects with this exact name")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    init_db()
    bound = 0
    skipped = 0
    with session_scope() as db:
        query = db.query(GeProject).filter(GeProject.deleted_at.is_(None))
        if args.project_id:
            query = query.filter(GeProject.id == args.project_id.strip())
        if args.project_name:
            query = query.filter(GeProject.name == args.project_name.strip())
        projects = query.order_by(GeProject.updated_at.desc()).all()
        if not projects:
            print("ok: no projects matched")
            return 0
        for project in projects:
            result = backfill_project(db, project, dry_run=args.dry_run)
            print(f"{result}: project={project.name!r} id={project.id}")
            if result.startswith("skip"):
                skipped += 1
            else:
                bound += 1
        if args.dry_run:
            db.rollback()
        print(f"done: processed={bound} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
