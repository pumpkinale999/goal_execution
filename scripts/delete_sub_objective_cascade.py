#!/usr/bin/env python3
"""Cascade-delete a sub-objective: projects → programs → objective.

Mirrors GE empty-checks:
  - soft-delete projects first (service actor may force non-empty)
  - delete program only when no active (non-soft-deleted) projects remain
  - delete objective only when no child objectives and no programs remain

This script only touches goal_execution. Soft-deleted projects leave orphan
``project-management`` notes / K27 bindings until you run skstudio::

    python backend/scripts/cleanup_orphan_project_notes.py --dry-run
    python backend/scripts/cleanup_orphan_project_notes.py --apply

Usage (from goal_execution repo root)::

    # Plan only (default)
    python scripts/delete_sub_objective_cascade.py --name 'AI原生医疗平台v1.0·3场景10院上线'

    # Or by id
    python scripts/delete_sub_objective_cascade.py --objective-id <uuid>

    # Actually mutate
    python scripts/delete_sub_objective_cascade.py --name '…' --apply

Production (SSH · read-only plan first)::

    # Load Postgres DATABASE_URL from /etc/goal-execution/goal-execution.env
    ssh devops@prod
    sudo bash -lc 'set -a; source /etc/goal-execution/goal-execution.env; set +a; \\
      cd /opt/goal_execution && sudo -u ge env HOME=/var/lib/ge \\
      .venv/bin/python scripts/delete_sub_objective_cascade.py --name \"…\"'
    # only after reviewing the plan:
    # … same command … --apply
    # then: skstudio cleanup_orphan_project_notes.py --apply
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.db import init_db, session_scope
from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_orchestrator import soft_delete_project
from app.services.ge_strategic import delete_objective, delete_program


SERVICE_ACTOR = AuthUser(user_id="cascade-delete-script", auth_method="service")


@dataclass
class CascadePlan:
    objective: GeObjective
    child_plans: list[CascadePlan] = field(default_factory=list)
    programs: list[tuple[GeProgram, list[GeProject]]] = field(default_factory=list)


def _find_objectives(
    db: Session,
    *,
    name: str | None,
    objective_id: str | None,
    level: str | None,
) -> list[GeObjective]:
    q = db.query(GeObjective)
    if objective_id:
        obj = db.get(GeObjective, objective_id)
        return [obj] if obj is not None else []
    assert name is not None
    q = q.filter(GeObjective.name == name)
    if level:
        q = q.filter(GeObjective.level == level)
    return q.order_by(GeObjective.created_at.asc()).all()


def _build_plan(db: Session, objective: GeObjective) -> CascadePlan:
    children = (
        db.query(GeObjective)
        .filter(GeObjective.parent_id == objective.id)
        .order_by(GeObjective.sort_order.asc(), GeObjective.created_at.asc())
        .all()
    )
    programs = (
        db.query(GeProgram)
        .filter(GeProgram.objective_id == objective.id)
        .order_by(GeProgram.sort_order.asc(), GeProgram.created_at.asc())
        .all()
    )
    prog_rows: list[tuple[GeProgram, list[GeProject]]] = []
    for program in programs:
        projects = (
            db.query(GeProject)
            .filter(
                GeProject.program_id == program.id,
                GeProject.deleted_at.is_(None),
            )
            .order_by(GeProject.sort_order.asc(), GeProject.created_at.asc())
            .all()
        )
        prog_rows.append((program, projects))
    return CascadePlan(
        objective=objective,
        child_plans=[_build_plan(db, child) for child in children],
        programs=prog_rows,
    )


def _print_plan(plan: CascadePlan, *, indent: int = 0) -> None:
    pad = "  " * indent
    obj = plan.objective
    print(
        f"{pad}objective  level={obj.level}  id={obj.id}  name={obj.name!r}  "
        f"lifecycle={obj.lifecycle_status}"
    )
    for child in plan.child_plans:
        _print_plan(child, indent=indent + 1)
    for program, projects in plan.programs:
        print(
            f"{pad}  program  id={program.id}  name={program.name!r}  "
            f"lifecycle={program.lifecycle_status}  active_projects={len(projects)}"
        )
        for project in projects:
            print(
                f"{pad}    project  id={project.id}  name={project.name!r}  "
                f"status={project.status}  → soft-delete"
            )
        print(f"{pad}  → delete program {program.id}")
    print(f"{pad}→ delete objective {obj.id}")


def _apply_plan(db: Session, plan: CascadePlan) -> None:
    for child in plan.child_plans:
        _apply_plan(db, child)
    for program, projects in plan.programs:
        for project in projects:
            print(f"soft-delete project {project.id}  {project.name!r}")
            soft_delete_project(db, project.id, SERVICE_ACTOR)
        print(f"delete program {program.id}  {program.name!r}")
        delete_program(db, program.id)
    obj = plan.objective
    print(f"delete objective {obj.id}  {obj.name!r}")
    delete_objective(db, obj.id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cascade-delete sub-objective: projects → programs → objective",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--name", help="Exact objective name match")
    target.add_argument("--objective-id", help="Objective id")
    parser.add_argument(
        "--level",
        default="sub",
        help="When matching by --name, require this level (default: sub; use '' to skip)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete (default is dry-run / plan only)",
    )
    args = parser.parse_args(argv)

    level = args.level if args.level else None
    init_db()
    with session_scope() as db:
        matches = _find_objectives(
            db,
            name=args.name,
            objective_id=args.objective_id,
            level=level,
        )
        if not matches:
            print("no matching objective", file=sys.stderr)
            return 1
        if len(matches) > 1:
            print(
                f"ambiguous: {len(matches)} objectives match; "
                "use --objective-id to pick one:",
                file=sys.stderr,
            )
            for obj in matches:
                print(
                    f"  id={obj.id}  level={obj.level}  name={obj.name!r}",
                    file=sys.stderr,
                )
            return 2

        plan = _build_plan(db, matches[0])
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"=== {mode} cascade plan ===")
        _print_plan(plan)
        if not args.apply:
            print("\n(no changes; re-run with --apply to mutate)")
            return 0

        _apply_plan(db, plan)
        print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
