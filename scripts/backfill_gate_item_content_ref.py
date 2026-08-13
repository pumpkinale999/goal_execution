#!/usr/bin/env python3
"""Backfill GateItem evidence content_ref from project root Note (v2.38.67).

Idempotent: does not overwrite existing content_ref (incl. legacy https/att).
Missing ref + project_note_id → kb:{project_note_id}. No root → skip + report.

Usage (from goal_execution repo root)::

    python scripts/backfill_gate_item_content_ref.py --dry-run
    python scripts/backfill_gate_item_content_ref.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.db import init_db, session_scope
from app.models.ge import GeGateItem, GePhase, GeProject
from app.services.ge_content_ref_migration import plan_content_ref_backfill


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill gate item content_ref from project root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    init_db()
    filled = 0
    kept = 0
    skipped = 0
    with session_scope() as db:
        rows = (
            db.query(GeGateItem, GeProject)
            .join(GePhase, GePhase.id == GeGateItem.phase_id)
            .join(GeProject, GeProject.id == GePhase.project_id)
            .filter(GeProject.deleted_at.is_(None))
            .all()
        )
        for item, project in rows:
            new_payload, reason = plan_content_ref_backfill(
                item.payload_dict,
                project_note_id=project.project_note_id,
                status=item.status,
            )
            if reason == "filled_root" and new_payload is not None:
                filled += 1
                if not args.dry_run:
                    item.payload_dict = new_payload
            elif reason == "keep_existing":
                kept += 1
            else:
                skipped += 1
    mode = "dry-run" if args.dry_run else "applied"
    print(f"{mode}: filled={filled} kept={kept} skipped_no_root={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
