"""GE-T169～T171 · M36 queues ready / B3 / governor."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_PM,
    U_ZHANGSAN,
    create_project,
    get_graph,
    phase_by_name,
)


def _gi(graph: dict, name: str) -> dict:
    return next(
        gi
        for phase in graph["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == name
    )


def _submit_row(queues: dict, gate_item_id: str) -> dict | None:
    return next((s for s in queues["submit"] if s["gate_item_id"] == gate_item_id), None)


def test_ge_t169_not_yet_started_in_submit_queue(client):
    """GE-T169 · structure OK + phase start future → submit · ready=false · not_yet_started."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = _gi(graph, "诊断报告")
    # Golden 方案 window starts 2026-06-01 → before that = not Ready
    with patch("app.services.ge_queues.today_shanghai", return_value=date(2026, 5, 15)):
        q = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_ZHANGSAN))
    assert q.status_code == 200, q.text
    row = _submit_row(q.json(), gi["id"])
    assert row is not None
    assert row["ready"] is False
    assert row["block_reason"] == "not_yet_started"
    assert row["phase_id"]
    assert row["phase_effective_planned_start"] == "2026-06-01"
    assert row.get("as_governor") is False


def test_ge_t170_ready_when_start_reached_or_missing(client):
    """GE-T170 · start≤today → ready=true; PM proxy → as_governor; absent start → Ready."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = _gi(graph, "诊断报告")

    with patch("app.services.ge_queues.today_shanghai", return_value=date(2026, 6, 10)):
        q = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_ZHANGSAN))
        q_pm = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_PM))
    assert q.status_code == 200
    row = _submit_row(q.json(), gi["id"])
    assert row is not None
    assert row["ready"] is True
    assert row["block_reason"] is None

    pm_row = _submit_row(q_pm.json(), gi["id"])
    assert pm_row is not None
    assert pm_row["as_governor"] is True
    assert pm_row["ready"] is True

    # Unit: no effective / planned start → Ready
    from app.services.ge_queues import _ready_fields
    from types import SimpleNamespace

    phase = SimpleNamespace(id="ph", sequence=1, planned_start=None, planned_end=None, name="x", is_system=False)
    meta = _ready_fields(phase, [phase], None, date(2026, 6, 10))
    assert meta["ready"] is True
    assert meta["block_reason"] is None
    assert meta["phase_effective_planned_start"] is None


def test_ge_t171_no_produce_not_in_submit(client):
    """GE-T171 · gate item without produce link → not in submit (B3)."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    plan = phase_by_name(graph, "方案")
    add = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{plan['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "无产出门控", "form": "material", "planned_due": "2026-06-12"},
    )
    assert add.status_code == 200, add.text
    new_gi = next(
        gi
        for phase in add.json()["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == "无产出门控"
    )
    with patch("app.services.ge_queues.today_shanghai", return_value=date(2026, 6, 10)):
        q_assignee = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_ZHANGSAN))
        q_pm = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_PM))
    assert _submit_row(q_assignee.json(), new_gi["id"]) is None
    assert _submit_row(q_pm.json(), new_gi["id"]) is None
