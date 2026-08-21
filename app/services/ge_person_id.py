"""M42 Person column validation (§3.3.1 · normative ^\\d+$)."""

from __future__ import annotations

import re

from fastapi import HTTPException

PERSON_USER_ID_RE = re.compile(r"^\d+$")


def require_person_user_id(value: str) -> str:
    """Non-empty values must match ``^\\d+$``; empty returns ``""`` (caller picks semantic error)."""
    stripped = str(value or "").strip()
    if not stripped:
        return stripped
    if not PERSON_USER_ID_RE.fullmatch(stripped):
        raise HTTPException(status_code=400, detail={"detail": "invalid_person_user_id"})
    return stripped


def optional_person_user_id(value: str | None) -> str | None:
    """Nullable Person column: None/blank → None; non-empty must be numeric."""
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    return require_person_user_id(stripped)
