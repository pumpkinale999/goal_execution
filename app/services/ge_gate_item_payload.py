"""GateItem form definition and submit payload validation (§3.4.1 · §5.1)."""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

VALID_FORMS = frozenset({"material", "metric", "status"})
METRIC_OPERATORS = frozenset({">=", "<=", "==", ">", "<"})
_CONTENT_REF_RE = re.compile(r"^(https?://.+|kb:[0-9a-f-]{36}|att:[0-9a-f-]{36})$", re.I)


def _parse_bool(raw: Any) -> bool | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in ("true", "1", "yes", "是"):
        return True
    if text in ("false", "0", "no", "否"):
        return False
    return None


def parse_form(raw: Any) -> str:
    form = str(raw or "material").strip().lower()
    if form not in VALID_FORMS:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return form


def definition_from_body(form: str, body: dict[str, Any]) -> dict[str, Any]:
    if form == "material":
        return {}
    if form == "metric":
        target_value = body.get("target_value")
        operator = str(body.get("operator") or "").strip()
        if target_value is None or str(target_value).strip() == "":
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        if operator not in METRIC_OPERATORS:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        return {"target_value": target_value, "operator": operator}
    target_state = str(body.get("target_state") or "").strip()
    if not target_state:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    target_value = _parse_bool(body.get("target_value"))
    if target_value is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return {"target_state": target_state, "target_value": target_value}


def merge_definition_patch(existing: dict[str, Any], form: str, body: dict[str, Any]) -> dict[str, Any]:
    if form == "material":
        return {}
    if form == "metric":
        merged = dict(existing)
        if "target_value" in body:
            target_value = body.get("target_value")
            if target_value is None or str(target_value).strip() == "":
                raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
            merged["target_value"] = target_value
        if "operator" in body:
            operator = str(body.get("operator") or "").strip()
            if operator not in METRIC_OPERATORS:
                raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
            merged["operator"] = operator
        if not merged.get("target_value") or not merged.get("operator"):
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        return merged
    merged = dict(existing)
    if "target_state" in body:
        target_state = str(body.get("target_state") or "").strip()
        if not target_state:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        merged["target_state"] = target_state
    if "target_value" in body:
        target_value = _parse_bool(body.get("target_value"))
        if target_value is None:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        merged["target_value"] = target_value
    if not merged.get("target_state") or merged.get("target_value") is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return merged


def validate_submit_payload(
    form: str,
    payload: dict[str, Any],
    existing: dict[str, Any],
    *,
    project_note_id: str | None = None,
) -> dict[str, Any]:
    if form == "material":
        summary = str(payload.get("summary") or "").strip()
        if not summary:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        if not project_note_id:
            raise HTTPException(status_code=409, detail={"detail": "project_note_required"})
        content_ref = payload.get("content_ref")
        if content_ref is None or not str(content_ref).strip():
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        content_ref = str(content_ref).strip()
        if not _CONTENT_REF_RE.match(content_ref):
            raise HTTPException(status_code=400, detail={"detail": "invalid_content_ref"})
        expected = f"kb:{project_note_id}"
        if content_ref.lower() != expected.lower():
            raise HTTPException(status_code=400, detail={"detail": "invalid_content_ref"})
        return {"summary": summary, "content_ref": content_ref}

    summary = str(payload.get("summary") or "").strip()
    if not summary:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})

    if form == "metric":
        actual_value = payload.get("actual_value")
        if actual_value is None or str(actual_value).strip() == "":
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        base = {
            "target_value": existing.get("target_value"),
            "operator": existing.get("operator"),
            "actual_value": actual_value,
            "summary": summary,
        }
        if base["target_value"] is None or not base["operator"]:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        return base

    actual_value = _parse_bool(payload.get("actual_value"))
    if actual_value is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    merged: dict[str, Any] = {
        "target_state": existing.get("target_state"),
        "target_value": existing.get("target_value"),
        "actual_value": actual_value,
        "summary": summary,
    }
    if not merged["target_state"] or merged["target_value"] is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return merged
