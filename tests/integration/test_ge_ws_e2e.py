"""WS callback integration test (§5.4)."""

from __future__ import annotations

from unittest.mock import patch

import httpx


def test_ge_ws_callback_posts_fanout(ge_db, monkeypatch):
    monkeypatch.setenv("SKSTUDIO_INTERNAL_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("GOAL_EXECUTION_SERVICE_TOKEN", "test-service-token")
    from app.config import get_settings

    get_settings.cache_clear()
    calls: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            calls.append((url, json or {}))
            req = httpx.Request("POST", url)
            return httpx.Response(200, json={"delivered": 1, "skipped_offline": 0}, request=req)

    with patch("app.services.ge_ws_callback.httpx.Client", FakeClient):
        from app.services.ge_ws_callback import dispatch_ws_events

        dispatch_ws_events(
            None,
            [
                {
                    "event": "ge.gate.opened",
                    "target_user_ids": ["1"],
                    "payload": {"project_id": "p1", "phase_name": "开发", "sequence": 2},
                }
            ],
        )

    assert calls
    assert calls[0][0].endswith("/internal/ge/ws-fanout")
    assert calls[0][1]["event"] == "ge.gate.opened"
