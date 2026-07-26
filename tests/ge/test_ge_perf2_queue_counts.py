"""GE-PERF2.1 · project-queue-counts vs build_queues map · TTL · schema."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from app.services import ge_queues
from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, U_ZHANGSAN, create_project, get_graph


def _gi(graph: dict, name: str) -> dict:
    return next(
        gi for phase in graph["phases"] for gi in phase["gate_items"] if gi["name"] == name
    )


def _map_from_queues(queues: dict) -> dict[str, int]:
    return ge_queues._counts_from_queues(queues)


def test_ge_perf2_02_counts_match_queues_map(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = _gi(graph, "诊断报告")
    assert gi

    ge_queues.invalidate_project_queue_counts()
    with patch("app.services.ge_queues.today_shanghai", return_value=date(2026, 6, 10)):
        q = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_ZHANGSAN))
        c = client.get("/api/v1/ge/me/project-queue-counts", headers=jwt_headers(U_ZHANGSAN))
    assert q.status_code == 200, q.text
    assert c.status_code == 200, c.text
    body = c.json()
    assert set(body.keys()) == {"counts"}
    assert body["counts"] == _map_from_queues(q.json())


def test_ge_perf2_09_response_has_only_counts(client):
    create_project(client, U_PM)
    ge_queues.invalidate_project_queue_counts()
    r = client.get("/api/v1/ge/me/project-queue-counts", headers=jwt_headers(U_PM))
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"counts"}
    for forbidden in ("submit", "sign", "deviation_actions", "actionable_tasks", "ready_tasks"):
        assert forbidden not in body


def test_ge_perf2_e01_ttl_skips_rebuild(client, monkeypatch):
    create_project(client, U_PM)
    ge_queues.invalidate_project_queue_counts()
    calls = {"n": 0}
    real = ge_queues.build_queues

    def spy(db, user_id):
        calls["n"] += 1
        return real(db, user_id)

    monkeypatch.setattr(ge_queues, "build_queues", spy)
    h = jwt_headers(U_PM)
    assert client.get("/api/v1/ge/me/project-queue-counts", headers=h).status_code == 200
    assert calls["n"] == 1
    assert client.get("/api/v1/ge/me/project-queue-counts", headers=h).status_code == 200
    assert calls["n"] == 1
    ge_queues.invalidate_project_queue_counts()
    assert client.get("/api/v1/ge/me/project-queue-counts", headers=h).status_code == 200
    assert calls["n"] == 2
