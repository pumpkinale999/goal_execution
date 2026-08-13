"""GateItem form definition and submit payload validation (§3.4.1 · evidence layer)."""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from app.services.ge_note_project_guard import get_note_project_guard

VALID_FORMS = frozenset({"material", "metric", "status"})
METRIC_OPERATORS = frozenset({">=", "<=", "==", ">", "<"})
# New submits: kb:{uuid} only (no fragment, no https/att).
_KB_CONTENT_REF_RE = re.compile(r"^kb:([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$", re.I)


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


def parse_kb_note_id(content_ref: str) -> str | None:
    text = str(content_ref or "").strip()
    if not text or "#" in text:
        return None
    match = _KB_CONTENT_REF_RE.match(text)
    return match.group(1) if match else None


def require_explicit_content_ref(
    payload: dict[str, Any],
    *,
    project_id: str,
    project_note_id: str | None,
) -> str:
    """Validate and return content_ref; never server-fills root on submit."""
    if not project_note_id:
        raise HTTPException(status_code=409, detail={"detail": "project_note_required"})
    raw = payload.get("content_ref")
    if raw is None or not str(raw).strip():
        raise HTTPException(status_code=400, detail={"detail": "invalid_content_ref"})
    content_ref = str(raw).strip()
    if "#" in content_ref:
        raise HTTPException(status_code=400, detail={"detail": "invalid_content_ref"})
    note_id = parse_kb_note_id(content_ref)
    if not note_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_content_ref"})
    get_note_project_guard().assert_in_project(project_id=project_id, note_id=note_id)
    return f"kb:{note_id.lower()}"


def assert_content_ref_still_available(
    *,
    project_id: str,
    content_ref: str | None,
    project_note_id: str | None,
) -> None:
    """Sign-time existence check."""
    if not project_note_id:
        raise HTTPException(status_code=409, detail={"detail": "project_note_required"})
    if not content_ref or not str(content_ref).strip():
        raise HTTPException(status_code=400, detail={"detail": "content_ref_note_unavailable"})
    note_id = parse_kb_note_id(str(content_ref).strip())
    if not note_id:
        raise HTTPException(status_code=400, detail={"detail": "content_ref_note_unavailable"})
    get_note_project_guard().assert_in_project(project_id=project_id, note_id=note_id)


def optional_content_ref_from_body(body: dict[str, Any]) -> str | None:
    if "content_ref" not in body:
        return None
    raw = body.get("content_ref")
    if raw is None or not str(raw).strip():
        return None
    content_ref = str(raw).strip()
    if "#" in content_ref or not parse_kb_note_id(content_ref):
        raise HTTPException(status_code=400, detail={"detail": "invalid_content_ref"})
    return content_ref


def definition_from_body(form: str, body: dict[str, Any]) -> dict[str, Any]:
    content_ref = optional_content_ref_from_body(body)
    if form == "material":
        out: dict[str, Any] = {}
        if content_ref:
            out["content_ref"] = content_ref
        return out
    if form == "metric":
        target_value = body.get("target_value")
        operator = str(body.get("operator") or "").strip()
        if target_value is None or str(target_value).strip() == "":
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        if operator not in METRIC_OPERATORS:
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        out = {"target_value": target_value, "operator": operator}
        if content_ref:
            out["content_ref"] = content_ref
        return out
    target_state = str(body.get("target_state") or "").strip()
    if not target_state:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    target_value = _parse_bool(body.get("target_value"))
    if target_value is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    out = {"target_state": target_state, "target_value": target_value}
    if content_ref:
        out["content_ref"] = content_ref
    return out


def merge_definition_patch(existing: dict[str, Any], form: str, body: dict[str, Any]) -> dict[str, Any]:
    content_ref = optional_content_ref_from_body(body)
    if form == "material":
        merged: dict[str, Any] = {}
        if content_ref is not None:
            merged["content_ref"] = content_ref
        elif existing.get("content_ref"):
            merged["content_ref"] = existing["content_ref"]
        return merged
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
        if content_ref is not None:
            merged["content_ref"] = content_ref
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
    if content_ref is not None:
        merged["content_ref"] = content_ref
    if not merged.get("target_state") or merged.get("target_value") is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return merged


def validate_submit_payload(
    form: str,
    payload: dict[str, Any],
    existing: dict[str, Any],
    *,
    project_id: str,
    project_note_id: str | None = None,
) -> dict[str, Any]:
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    content_ref = require_explicit_content_ref(
        payload,
        project_id=project_id,
        project_note_id=project_note_id,
    )

    if form == "material":
        return {"summary": summary, "content_ref": content_ref}

    if form == "metric":
        actual_value = payload.get("actual_value")
        if actual_value is None or str(actual_value).strip() == "":
            raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
        base = {
            "target_value": existing.get("target_value"),
            "operator": existing.get("operator"),
            "actual_value": actual_value,
            "summary": summary,
            "content_ref": content_ref,
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
        "content_ref": content_ref,
    }
    if not merged["target_state"] or merged["target_value"] is None:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return merged
