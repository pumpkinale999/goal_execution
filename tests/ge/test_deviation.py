"""GE-T69–T82 · M22 Deviation."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from app.constants import SYSTEM_START_GATE_ITEM_NAME, SYSTEM_START_TASK_TITLE
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_WANGWU,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    phase_by_name,
    task_id_by_title,
)


def _gi(graph: dict, name: str) -> dict:
    return next(
        gi
        for phase in graph["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == name
    )


def _open_overdue_deviation(client, graph, pm=U_PM):
    gi = _gi(graph, "诊断报告")
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        resp = client.post(
            f"/api/v1/ge/gate-items/{gi['id']}/deviations/open",
            headers=jwt_headers(pm),
            json={"kind": "overdue"},
        )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_overdue_projection(client):
    """GE-T69 · overdue projection · deviation hides overdue stamp."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = _gi(graph, "诊断报告")
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        graph2 = get_graph(client, created["id"], U_PM)
        gi2 = _gi(graph2, "诊断报告")
        assert gi2["is_overdue"] is True
        assert gi2.get("deviation") is None

    _open_overdue_deviation(client, graph, U_PM)
    graph3 = get_graph(client, created["id"], U_PM)
    gi3 = _gi(graph3, "诊断报告")
    assert gi3["status"] == "deviation"
    assert gi3["is_overdue"] is False
    assert gi3["deviation"]["status"] == "open"


def test_open_deviation_rebind(client):
    """GE-T70 · Produce rebind · deviated · GI deviation."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    graph2 = get_graph(client, created["id"], U_PM)
    orig = next(t for t in graph2["phases"][1]["tasks"] if t["title"] == "编写诊断报告")
    assert orig["status"] == "deviated"
    assert orig["produces"] == []
    remediation = next(t for t in graph2["phases"][1]["tasks"] if t["title"].startswith("补救·"))
    assert remediation["produces"] == [_gi(graph2, "诊断报告")["id"]]
    assert _gi(graph2, "诊断报告")["status"] == "deviation"
    dev = _gi(graph2, "诊断报告")["deviation"]
    assert dev["remediation_task_id"] == remediation["id"]
    assert dev["superseded_task_id"] == orig["id"]


def test_deviated_task_no_produce_edge(client):
    """GE-T70 · deviated task has no produce edge."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    graph2 = get_graph(client, created["id"], U_PM)
    for edge in graph2["edges"]:
        if edge["kind"] == "produce":
            task_id = edge["from"]["id"]
            task = next(
                t
                for phase in graph2["phases"]
                for t in phase["tasks"]
                if t["id"] == task_id
            )
            assert task["status"] != "deviated"


def test_open_twice_409(client):
    """GE-T71 · duplicate open."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    gi = _gi(graph, "诊断报告")
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        resp = client.post(
            f"/api/v1/ge/gate-items/{gi['id']}/deviations/open",
            headers=jwt_headers(U_PM),
            json={"kind": "overdue"},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "deviation_already_open"


def test_activate_deviation(client, monkeypatch):
    """GE-T72 · activate · planned_due sync."""
    pa_calls: list[dict] = []

    def _fake_pa(**kwargs):
        pa_calls.append(kwargs)

    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", _fake_pa)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    dev_id = body["deviation"]["id"]
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "activate",
            "reason": "范围扩大",
            "remediation_plan": "补交简化版",
            "remediation_due": "2026-07-01",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["deviation"]["status"] == "active"
    assert data["gate_item"]["planned_due"] == "2026-07-01"
    assert pa_calls
    assert pa_calls[0]["event"] == "ge.deviation.activated"


def test_open_phase_start_allowed_submit_done_409(client):
    """GE-T81 · open phase: start ok · submit/done 409."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    open_body = _open_overdue_deviation(client, graph)
    remediation_id = next(
        t["id"]
        for phase in get_graph(client, created["id"], U_PM)["phases"]
        for t in phase["tasks"]
        if t.get("is_remediation")
    )
    start = client.post(
        f"/api/v1/ge/tasks/{remediation_id}/start",
        headers=jwt_headers(U_ZHANGSAN),
    )
    assert start.status_code == 200, start.text
    gi = _gi(get_graph(client, created["id"], U_PM), "诊断报告")
    submit = client.post(
        f"/api/v1/ge/gate-items/{gi['id']}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("补救提交"),
    )
    assert submit.status_code == 409
    assert submit.json()["detail"] == "deviation_not_activated"
    done = client.post(
        f"/api/v1/ge/tasks/{remediation_id}/done",
        headers=jwt_headers(U_ZHANGSAN),
    )
    assert done.status_code == 409


def test_system_node_open_403(client):
    """GE-T82 · system GI cannot open deviation."""
    created = create_project(client, U_PM, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    start_gi = next(
        gi for gi in phase_by_name(graph, "开始")["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME
    )
    resp = client.post(
        f"/api/v1/ge/gate-items/{start_gi['id']}/deviations/open",
        headers=jwt_headers(U_PM),
        json={"kind": "scope"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "system_node_not_deviatable"


def test_remediation_submit_sign_close(client, monkeypatch):
    """GE-T73 · remediation flow closes deviation."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    open_body = _open_overdue_deviation(client, graph)
    dev_id = open_body["deviation"]["id"]
    client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "activate",
            "reason": "r",
            "remediation_plan": "p",
            "remediation_due": "2026-07-01",
        },
    )
    graph2 = get_graph(client, created["id"], U_PM)
    remediation_id = next(t["id"] for phase in graph2["phases"] for t in phase["tasks"] if t.get("is_remediation"))
    client.post(f"/api/v1/ge/tasks/{remediation_id}/start", headers=jwt_headers(U_ZHANGSAN))
    client.post(f"/api/v1/ge/tasks/{remediation_id}/done", headers=jwt_headers(U_ZHANGSAN))
    gi = _gi(graph2, "诊断报告")
    client.post(
        f"/api/v1/ge/gate-items/{gi['id']}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("补救完成"),
    )
    sign = client.post(
        f"/api/v1/ge/gate-items/{gi['id']}/sign",
        headers=jwt_headers(U_PM),
    )
    assert sign.status_code == 200, sign.text
    detail = client.get(f"/api/v1/ge/deviations/{dev_id}", headers=jwt_headers(U_PM))
    assert detail.json()["status"] == "closed"


def test_extend_revision_plan_required(client, monkeypatch):
    """GE-T74 · extend revision and plan required at >=3."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev_id = _open_overdue_deviation(client, graph)["deviation"]["id"]
    client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "activate",
            "reason": "r",
            "remediation_plan": "p",
            "remediation_due": "2026-07-01",
        },
    )
    for i in range(2):
        resp = client.patch(
            f"/api/v1/ge/deviations/{dev_id}",
            headers=jwt_headers(U_PM),
            json={
                "action": "extend",
                "remediation_due": f"2026-07-{10 + i}",
                "extend_reason": f"延期{i}",
            },
        )
        assert resp.status_code == 200, resp.text
    bad = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "extend",
            "remediation_due": "2026-08-01",
            "extend_reason": "need plan",
        },
    )
    assert bad.status_code == 400
    ok = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "extend",
            "remediation_due": "2026-08-01",
            "extend_reason": "need plan",
            "remediation_plan": "updated plan",
        },
    )
    assert ok.status_code == 200
    assert ok.json()["deviation"]["revision"] == 3


def test_cancel_snapshot_rollback(client):
    """GE-T79 · cancel restores produce and statuses."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    orig_task = next(t for t in graph["phases"][1]["tasks"] if t["title"] == "编写诊断报告")
    orig_status = orig_task["status"]
    dev_id = _open_overdue_deviation(client, graph)["deviation"]["id"]
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "cancel", "cancel_reason": "方案变更"},
    )
    assert resp.status_code == 200, resp.text
    graph2 = get_graph(client, created["id"], U_PM)
    gi = _gi(graph2, "诊断报告")
    assert gi["status"] in (orig_status, "draft", "rejected", "ready")
    task = next(t for t in graph2["phases"][1]["tasks"] if t["title"] == "编写诊断报告")
    assert task["status"] != "deviated"
    assert gi["id"] in task["produces"]
    detail = client.get(f"/api/v1/ge/deviations/{dev_id}", headers=jwt_headers(U_PM))
    assert detail.json()["status"] == "cancelled"


def test_deviation_produce_immutable_on_unlink(client):
    """GE-T87 · open/active deviation: remediation produce cannot be removed manually."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    graph2 = get_graph(client, created["id"], U_PM)
    gi = _gi(graph2, "诊断报告")
    remediation = next(t for t in graph2["phases"][1]["tasks"] if t.get("is_remediation"))
    resp = client.delete(
        f"/api/v1/ge/tasks/{remediation['id']}/produces/{gi['id']}",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "deviation_produce_immutable"
    graph3 = get_graph(client, created["id"], U_PM)
    assert any(
        edge["kind"] == "produce"
        and edge["from"]["id"] == remediation["id"]
        and edge["to"]["id"] == gi["id"]
        for edge in graph3["edges"]
    )


def test_deviated_task_patch_immutable(client):
    """GE-T88 · deviated task cannot be patched."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    graph2 = get_graph(client, created["id"], U_PM)
    deviated = next(t for t in graph2["phases"][1]["tasks"] if t["status"] == "deviated")
    resp = client.patch(
        f"/api/v1/ge/tasks/{deviated['id']}",
        headers=jwt_headers(U_PM),
        json={"title": "不应成功"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "task_deviated_immutable"


def test_remediation_task_not_deletable(client):
    """GE-T89 · remediation / deviated tasks cannot be deleted."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    graph2 = get_graph(client, created["id"], U_PM)
    remediation = next(t for t in graph2["phases"][1]["tasks"] if t.get("is_remediation"))
    deviated = next(t for t in graph2["phases"][1]["tasks"] if t["status"] == "deviated")
    rem_resp = client.delete(f"/api/v1/ge/tasks/{remediation['id']}", headers=jwt_headers(U_PM))
    assert rem_resp.status_code == 409
    assert rem_resp.json()["detail"] == "remediation_task_not_deletable"
    dev_resp = client.delete(f"/api/v1/ge/tasks/{deviated['id']}", headers=jwt_headers(U_PM))
    assert dev_resp.status_code == 409
    assert dev_resp.json()["detail"] == "task_deviated_immutable"
