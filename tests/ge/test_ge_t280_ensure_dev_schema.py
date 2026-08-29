"""GE-T280 · ensure_dev_schema refuses stamp when behind head."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ensure_dev_schema.py"
_spec = importlib.util.spec_from_file_location("ensure_dev_schema", _SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def test_ge_t280_decide_schema_action():
    decide = _mod.decide_schema_action
    assert decide(current=None, head_rev="033_drop_ge_org_tables") == "stamp"
    assert decide(current="033_drop_ge_org_tables", head_rev="033_drop_ge_org_tables") == "ok"
    assert decide(current="032_drop_dept_org_fk", head_rev="033_drop_ge_org_tables") == "refuse"
