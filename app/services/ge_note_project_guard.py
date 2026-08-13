"""Note ∈ project tree guard for GateItem evidence content_ref (v2.38.67+)."""

from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException


class NoteProjectGuard(Protocol):
    def assert_in_project(self, *, project_id: str, note_id: str) -> None:
        """Raise HTTPException if note_id is not a live note under project_id's tree."""


class AcceptAllNoteProjectGuard:
    """Test / migration helper: any kb uuid is accepted."""

    def assert_in_project(self, *, project_id: str, note_id: str) -> None:
        return None


class MappingNoteProjectGuard:
    """Test helper: map (project_id, note_id) → reason (ok|not_in_tree|…)."""

    def __init__(self, outcomes: dict[tuple[str, str], str] | None = None, *, default: str = "ok"):
        self.outcomes = outcomes or {}
        self.default = default

    def assert_in_project(self, *, project_id: str, note_id: str) -> None:
        reason = self.outcomes.get((project_id, note_id), self.default)
        _raise_for_reason(reason)


class UnavailableNoteProjectGuard:
    """Simulates KB down."""

    def assert_in_project(self, *, project_id: str, note_id: str) -> None:
        raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"})


def _raise_for_reason(reason: str) -> None:
    if reason in ("ok", ""):
        return
    if reason == "not_found":
        raise HTTPException(status_code=400, detail={"detail": "content_ref_note_unavailable"})
    if reason == "unavailable":
        raise HTTPException(status_code=400, detail={"detail": "content_ref_note_unavailable"})
    if reason == "project_binding_missing":
        raise HTTPException(status_code=400, detail={"detail": "project_binding_missing"})
    if reason == "invalid_note_id":
        raise HTTPException(status_code=400, detail={"detail": "invalid_content_ref"})
    if reason == "note_validation_unavailable":
        raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"})
    raise HTTPException(status_code=400, detail={"detail": "note_not_in_project"})


_active_guard: NoteProjectGuard | None = None


def get_note_project_guard() -> NoteProjectGuard:
    global _active_guard
    if _active_guard is not None:
        return _active_guard
    from app.config import get_settings

    settings = get_settings()
    base = (getattr(settings, "kbase_base_url", None) or "").strip()
    token = (getattr(settings, "kbase_service_token", None) or "").strip()
    if base and token:
        from app.services.ge_kbase_note_guard import HttpNoteProjectGuard

        return HttpNoteProjectGuard(
            base_url=base,
            service_token=token,
            timeout_seconds=float(getattr(settings, "kbase_assert_timeout_seconds", 2.5) or 2.5),
        )
    return _UnconfiguredGuard()


def set_note_project_guard(guard: NoteProjectGuard | None) -> None:
    global _active_guard
    _active_guard = guard


class _UnconfiguredGuard:
    def assert_in_project(self, *, project_id: str, note_id: str) -> None:
        raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"})
