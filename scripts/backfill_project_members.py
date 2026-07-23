#!/usr/bin/env python3
"""Backfill project members roster (M37).

Usage (from goal_execution repo root)::

    python scripts/backfill_project_members.py --dry-run
    python scripts/backfill_project_members.py
    python scripts/backfill_project_members.py --with-assignees
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.db import init_db, session_scope
from app.models.ge import GeProject
from app.services.ge_project_members import (
    ensure_members_for_project_assignees,
    upsert_pm,
)


def backfill_project(db, project: GeProject, *, with_assignees: bool, dry_run: bool) -> str:
    if dry_run:
        parts = [f"pm={project.pm_user_id}"]
        if with_assignees:
            parts.append("with_assignees")
        return f"dry-run:would_ensure_{'+'.join(parts)}"
    upsert_pm(db, project_id=project.id, pm_user_id=project.pm_user_id)
    if with_assignees:
        ensure_members_for_project_assignees(db, project_id=project.id)
    return "ok:ensured"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill ge_project_members")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--with-assignees",
        action="store_true",
        help="Also upsert task assignees as member when missing",
    )
    args = parser.parse_args(argv)

    init_db()
    with session_scope() as db:
        projects = (
            db.query(GeProject)
            .filter(GeProject.deleted_at.is_(None))
            .order_by(GeProject.created_at.asc())
            .all()
        )
        if not projects:
            print("no projects")
            return 0
        for project in projects:
            result = backfill_project(
                db,
                project,
                with_assignees=args.with_assignees,
                dry_run=args.dry_run,
            )
            print(f"{project.id}\t{project.name}\t{result}")
        if not args.dry_run:
            db.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
