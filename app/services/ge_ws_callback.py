"""WS fanout callback to skstudio (§5.4)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings

logger = logging.getLogger(__name__)


def dispatch_ws_events(db: Session, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    settings = get_settings()
    base = (settings.skstudio_internal_url or "").strip().rstrip("/")
    token = (settings.goal_execution_service_token or "").strip()
    if not base or not token:
        return
    url = f"{base}/internal/ge/ws-fanout"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=5.0) as client:
        for event in events:
            try:
                resp = client.post(url, headers=headers, json=event)
                if resp.status_code >= 400:
                    logger.warning("ge_ws_fanout_failed status=%s body=%s", resp.status_code, resp.text)
            except Exception:
                logger.exception("ge_ws_fanout_failed")
