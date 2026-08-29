#!/usr/bin/env python3
"""GE-T270 · Ban GE app/ from importing deleted org models / querying org_departments.

Alembic history under alembic/versions is excluded.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "app"

FORBIDDEN_IMPORT = re.compile(r"from\s+app\.models\.org\b|import\s+app\.models\.org\b")
FORBIDDEN_TABLE = re.compile(r"\borg_departments\b")


def main() -> int:
    violations: list[str] = []
    for path in APP.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO)
        if FORBIDDEN_IMPORT.search(text):
            violations.append(f"{rel}: forbidden import app.models.org")
        if FORBIDDEN_TABLE.search(text):
            violations.append(f"{rel}: forbidden literal org_departments")
    if violations:
        print("GE-T270 FAIL:")
        for v in violations:
            print(f"  {v}")
        return 1
    print("GE-T270 OK: no app.models.org / org_departments in app/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
