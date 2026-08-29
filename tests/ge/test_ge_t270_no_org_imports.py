"""GE-T270 · CI ban: app/ must not import org models or reference org_departments."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_ge_t270_no_org_imports_in_app():
    script = REPO / "scripts" / "check_no_ge_org_imports.py"
    proc = subprocess.run([sys.executable, str(script)], cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
