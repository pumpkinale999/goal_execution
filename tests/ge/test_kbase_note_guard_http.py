"""M3 · GE→KB HttpNoteProjectGuard (MockTransport · no live KB required)."""

from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException

from app.services.ge_kbase_note_guard import HttpNoteProjectGuard
from app.services.ge_note_project_guard import AcceptAllNoteProjectGuard, set_note_project_guard
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    TEST_PROJECT_NOTE_ID,
    U_PM,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    task_id_by_title,
)


def _detail(exc_or_resp) -> str:
    if isinstance(exc_or_resp, HTTPException):
        d = exc_or_resp.detail
        return d.get("detail") if isinstance(d, dict) else str(d)
    body = exc_or_resp.json()
    d = body.get("detail", body)
    return d.get("detail") if isinstance(d, dict) else str(d)


def test_http_guard_ok_child():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/assert-note-in-project")
        return httpx.Response(200, json={"ok": True, "reason": "ok", "kind": "dir"})

    guard = HttpNoteProjectGuard(
        base_url="http://kbase.test",
        service_token="tok",
        transport=httpx.MockTransport(handler),
    )
    guard.assert_in_project(project_id="p1", note_id=TEST_PROJECT_NOTE_ID)


def test_http_guard_foreign_project():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "reason": "not_in_tree"})

    guard = HttpNoteProjectGuard(
        base_url="http://kbase.test",
        service_token="tok",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(HTTPException) as ei:
        guard.assert_in_project(project_id="p1", note_id=TEST_PROJECT_NOTE_ID)
    assert ei.value.status_code == 400
    assert _detail(ei.value) == "note_not_in_project"


def test_http_guard_kb_down_503():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("down")

    guard = HttpNoteProjectGuard(
        base_url="http://kbase.test",
        service_token="tok",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(HTTPException) as ei:
        guard.assert_in_project(project_id="p1", note_id=TEST_PROJECT_NOTE_ID)
    assert ei.value.status_code == 503
    assert _detail(ei.value) == "note_validation_unavailable"
    assert calls["n"] == 2  # one retry


def _start_x(client, graph):
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    return gi_x


def test_submit_via_http_guard_integration(client):
    """Cross-layer: submit path uses injected Http guard (child 200 / foreign 400 / down 503)."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi_x = _start_x(client, graph)

    def ok_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "reason": "ok"})

    set_note_project_guard(
        HttpNoteProjectGuard(
            base_url="http://kbase.test",
            service_token="tok",
            transport=httpx.MockTransport(ok_handler),
        )
    )
    ok = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("child"),
    )
    assert ok.status_code == 200, ok.text

    set_note_project_guard(AcceptAllNoteProjectGuard())
    created2 = create_project(client, U_PM)
    graph2 = get_graph(client, created2["id"], U_PM)
    gi2 = _start_x(client, graph2)

    def foreign_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "reason": "not_in_tree"})

    set_note_project_guard(
        HttpNoteProjectGuard(
            base_url="http://kbase.test",
            service_token="tok",
            transport=httpx.MockTransport(foreign_handler),
        )
    )
    bad = client.post(
        f"/api/v1/ge/gate-items/{gi2}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("x"),
    )
    assert bad.status_code == 400
    assert _detail(bad) == "note_not_in_project"

    set_note_project_guard(AcceptAllNoteProjectGuard())
    created3 = create_project(client, U_PM)
    graph3 = get_graph(client, created3["id"], U_PM)
    gi3 = _start_x(client, graph3)

    def down_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    set_note_project_guard(
        HttpNoteProjectGuard(
            base_url="http://kbase.test",
            service_token="tok",
            transport=httpx.MockTransport(down_handler),
        )
    )
    down = client.post(
        f"/api/v1/ge/gate-items/{gi3}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("x"),
    )
    assert down.status_code == 503
    assert _detail(down) == "note_validation_unavailable"