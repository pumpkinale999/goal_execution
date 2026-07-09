"""GE-T77 · GE-T80 · deviation queues."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, U_ZHANGSAN, create_project, get_graph


def _gi(graph: dict, name: str) -> dict:
    return next(
        gi
        for phase in graph["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == name
    )


def test_deviation_actions_queue(client):
    """GE-T77 · deviation_actions for PM."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = _gi(graph, "诊断报告")
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        q = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_PM))
    assert q.status_code == 200
    actions = q.json()["deviation_actions"]
    assert any(a["action"] == "open" and a["gate_item_id"] == gi["id"] for a in actions)

    client.post(
        f"/api/v1/ge/gate-items/{gi['id']}/deviations/open",
        headers=jwt_headers(U_PM),
        json={"kind": "overdue"},
    )
    q2 = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_PM))
    actions2 = q2.json()["deviation_actions"]
    assert len([a for a in actions2 if a["gate_item_id"] == gi["id"]]) == 1
    assert actions2[0]["action"] == "activate"


def test_submit_queue_includes_active_deviation(client):
    """GE-T80 · submit queue includes active deviation GI."""
    created = create_project(client, U_PM, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    gi = _gi(graph, "诊断报告")
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        client.post(
            f"/api/v1/ge/gate-items/{gi['id']}/deviations/open",
            headers=jwt_headers(U_PM),
            json={"kind": "overdue"},
        )
    dev_id = client.get(f"/api/v1/ge/projects/{created['id']}/graph", headers=jwt_headers(U_PM)).json()
    dev = _gi(dev_id, "诊断报告")["deviation"]["id"]
    activate = client.patch(
        f"/api/v1/ge/deviations/{dev}",
        headers=jwt_headers(U_PM),
        json={
            "action": "activate",
            "reason": "r",
            "remediation_plan": "p",
            "remediation_due": "2026-07-01",
        },
    )
    assert activate.status_code == 200, activate.text
    q = client.get("/api/v1/ge/me/queues", headers=jwt_headers(U_ZHANGSAN))
    assert q.status_code == 200
    submit = q.json()["submit"]
    assert any(s["gate_item_id"] == gi["id"] for s in submit)
