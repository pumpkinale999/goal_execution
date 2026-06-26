"""GE REST-only: submit/sign must not POST skstudio ws-fanout."""

from __future__ import annotations

from unittest.mock import MagicMock

from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    task_id_by_title,
)


def test_submit_sign_no_ws_fanout(client, monkeypatch):
    posts: list[str] = []

    class _FakeHttpxClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, **kwargs):
            posts.append(url)
            resp = MagicMock()
            resp.status_code = 200
            resp.text = ""
            return resp

    monkeypatch.setattr("app.services.ge_ws_callback.httpx.Client", _FakeHttpxClient)
    monkeypatch.setenv("SKSTUDIO_INTERNAL_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("GOAL_EXECUTION_SERVICE_TOKEN", "test-service-token")

    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")

    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))

    assert not any("ws-fanout" in url for url in posts)
