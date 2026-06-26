"""Personal-assistant notify callback to skstudio."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def dispatch_deviation_personal_assistant(
    *,
    event: str,
    recipient_user_ids: list[str],
    payload: dict[str, Any],
) -> None:
    if not recipient_user_ids:
        return
    settings = get_settings()
    base = (settings.skstudio_internal_url or "").strip().rstrip("/")
    token = (settings.goal_execution_service_token or "").strip()
    if not base or not token:
        return
    url = f"{base}/internal/ge/deviation-notify"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "event": event,
        "recipient_user_ids": recipient_user_ids,
        "payload": payload,
    }
    with httpx.Client(timeout=5.0) as client:
        try:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                logger.warning(
                    "ge_deviation_pa_notify_failed status=%s body=%s",
                    resp.status_code,
                    resp.text,
                )
        except Exception:
            logger.exception("ge_deviation_pa_notify_failed")
