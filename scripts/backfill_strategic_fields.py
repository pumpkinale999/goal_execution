#!/usr/bin/env python3
"""Backfill strategic fields on existing objectives/programs (M29 · §7.5)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings
from app.db import get_session_factory
from app.services.ge_strategic_backfill import run_strategic_backfill


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill M29 strategic fields")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    args = parser.parse_args()
    get_settings()
    factory = get_session_factory()
    session = factory()
    try:
        connection = session.connection()
        stats = run_strategic_backfill(connection, dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()
        print(stats)
    finally:
        session.close()


if __name__ == "__main__":
    main()
