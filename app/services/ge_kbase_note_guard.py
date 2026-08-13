"""HTTP client for KB assert-note-in-project (GateItem evidence · M3)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException

from app.services.ge_note_project_guard import _raise_for_reason

logger = logging.getLogger(__name__)

_ASSERT_PATH = "/api/v1/kbase/admin/assert-note-in-project"


class HttpNoteProjectGuard:
    """Call knowledge_base service; never cache ok results; one retry on transport error."""

    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        timeout_seconds: float = 2.5,
        actor_user_id: str = "goal_execution",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.timeout_seconds = timeout_seconds
        self.actor_user_id = actor_user_id
        self._transport = transport

    def assert_in_project(self, *, project_id: str, note_id: str) -> None:
        url = f"{self.base_url}{_ASSERT_PATH}"
        headers = {
            "Authorization": f"Bearer {self.service_token}",
            "X-Actor-User-Id": self.actor_user_id,
            "Content-Type": "application/json",
        }
        body = {"project_id": project_id, "note_id": note_id}
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self.timeout_seconds, transport=self._transport) as client:
                    resp = client.post(url, headers=headers, json=body)
                break
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt == 0:
                    continue
                logger.warning("kbase assert transport failed after retry: %s", exc)
                raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"}) from exc
        else:
            raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"}) from last_exc

        if resp.status_code >= 500:
            raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"})
        if resp.status_code == 401 or resp.status_code == 403:
            raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"})
        if resp.status_code >= 400:
            raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"})

        try:
            data: dict[str, Any] = resp.json()
        except Exception as exc:
            raise HTTPException(status_code=503, detail={"detail": "note_validation_unavailable"}) from exc

        if data.get("ok") is True:
            return
        reason = str(data.get("reason") or "not_in_tree")
        _raise_for_reason(reason)
