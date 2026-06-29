#!/usr/bin/env python3
"""One-shot migration of default-chain content to formal annual roots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings
from app.db import get_session_factory
from app.services.ge_default_chain_migrate import run_default_chain_migration_backfill


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate default chain content to formal annual roots")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    args = parser.parse_args()
    get_settings()
    factory = get_session_factory()
    session = factory()
    try:
        connection = session.connection()
        stats = run_default_chain_migration_backfill(connection, dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()
        print(stats)
    finally:
        session.close()


if __name__ == "__main__":
    main()
