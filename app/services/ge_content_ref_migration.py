"""Idempotent backfill of GateItem payload content_ref from project root Note."""

from __future__ import annotations

import json
from typing import Any


def plan_content_ref_backfill(
    payload: dict[str, Any] | Any,
    *,
    project_note_id: str | None,
    status: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Return (new_payload_or_None, reason).

    - Missing/blank content_ref + project_note_id → fill kb:{root}
    - Existing content_ref (incl. https/att) → keep (no overwrite)
    - No project_note_id → skip
    """
    if not isinstance(payload, dict):
        try:
            payload = json.loads(payload or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
    current = payload.get("content_ref")
    if current is not None and str(current).strip():
        return None, "keep_existing"
    if not project_note_id:
        return None, "skip_no_root"
    updated = dict(payload)
    updated["content_ref"] = f"kb:{project_note_id}"
    _ = status  # reserved; signed https/att already kept above
    return updated, "filled_root"
