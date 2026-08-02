"""GE-AUTHZ-T14 · OpenAPI contract for GE-AUTHZ paths (M7)."""

from __future__ import annotations

from pathlib import Path

import yaml

OPENAPI = Path(__file__).resolve().parents[2] / "openapi" / "ge-v1.yaml"

REQUIRED_PATHS = (
    "/ge/health",
    "/ge/goal-subtree-governor/check",
    "/ge/users/{user_id}/project-access",
    "/ge/portfolios/departments/{department_id}",
    "/ge/portfolios/teams/{team_id}",
    "/ge/portfolios/users/{user_id}",
)


def test_ge_authz_t14_openapi_version_and_paths() -> None:
    doc = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    assert doc["info"]["version"] == "1.26.1"
    paths = doc.get("paths") or {}
    missing = [p for p in REQUIRED_PATHS if p not in paths]
    assert missing == [], f"OpenAPI missing GE-AUTHZ paths: {missing}"
    blob = OPENAPI.read_text(encoding="utf-8")
    # Description may say "no /ge-api"; forbid path-like leftovers.
    assert "/ge-api/" not in blob
    assert "/api/v1/internal/ge" not in blob
    assert "is_goal_subtree_governor" in blob
    assert not any(p.startswith("/org/") and "goal-portfolio" in p for p in paths)
