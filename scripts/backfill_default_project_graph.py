#!/usr/bin/env python3
"""Rename system gate items + backfill empty-shell default proposal graph.

Usage (from goal_execution repo root)::

    python scripts/backfill_default_project_graph.py --dry-run
    python scripts/backfill_default_project_graph.py --apply
    python scripts/backfill_default_project_graph.py --apply --project-id <uuid>
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.db import init_db, session_scope
from app.models.ge import GeProject
from app.services.ge_default_graph_migration import apply_project_plan, plan_all_projects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill default project graph / rename system GIs")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default unless --apply)")
    parser.add_argument("--apply", action="store_true", help="Commit mutations")
    parser.add_argument("--project-id", default=None)
    args = parser.parse_args(argv)
    apply = bool(args.apply)
    if not apply:
        args.dry_run = True

    init_db()
    counts: Counter[str] = Counter()
    with session_scope() as db:
        plans = plan_all_projects(db, project_id=args.project_id)
        for plan in plans:
            counts[plan.action] += 1
            print(
                f"{plan.action}\t{plan.project_id}\t{plan.project_name}\t{plan.reason}"
                f"\trename_start={plan.rename_start}\trename_end={plan.rename_end}"
                f"\tfill={plan.fill_proposal}"
            )
            if apply and plan.action in ("shell_backfill", "rename_only"):
                project = db.get(GeProject, plan.project_id)
                if project is None:
                    continue
                apply_project_plan(db, project, plan)
        if not apply:
            db.rollback()

    mode = "applied" if apply else "dry-run"
    print(
        f"{mode}: shell_backfill={counts['shell_backfill']} rename_only={counts['rename_only']} "
        f"noop={counts['noop']} skip_anomaly={counts['skip_anomaly']} total={sum(counts.values())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
