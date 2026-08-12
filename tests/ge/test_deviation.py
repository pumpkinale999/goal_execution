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
    bootstrap_golden_phase_schedule,
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


def test_open_deviation_no_task_yet(client):
    """Open is time-first: GI→deviation, no remediation task / no produce rebind."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    graph2 = get_graph(client, created["id"], U_PM)
    orig = next(t for t in graph2["phases"][1]["tasks"] if t["title"] == "编写诊断报告")
    assert orig.get("status") != "deviated"
    assert orig.get("effective_status") != "deviated"
    assert _gi(graph2, "诊断报告")["id"] in (orig.get("produces") or [])
    assert not any(t["title"].startswith("补救·") for t in graph2["phases"][1]["tasks"])
    assert _gi(graph2, "诊断报告")["status"] == "deviation"
    dev = _gi(graph2, "诊断报告")["deviation"]
    assert dev["status"] == "open"
    assert not dev.get("remediation_task_id")
    assert dev["superseded_task_id"] == orig["id"]


def test_activate_creates_remediation_and_rebind(client, monkeypatch):
    """Activate confirms due → creates remediation task + produce rebind."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    dev_id = body["deviation"]["id"]
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    assert resp.status_code == 200, resp.text
    graph2 = get_graph(client, created["id"], U_PM)
    orig = next(t for t in graph2["phases"][1]["tasks"] if t["title"] == "编写诊断报告")
    assert orig["status"] == "deviated"
    assert orig["produces"] == []
    remediation = next(t for t in graph2["phases"][1]["tasks"] if t["title"].startswith("补救·"))
    assert remediation["produces"] == [_gi(graph2, "诊断报告")["id"]]
    dev = _gi(graph2, "诊断报告")["deviation"]
    assert dev["status"] == "active"
    assert dev["remediation_task_id"] == remediation["id"]


def test_remediation_task_patch_assignee_only(client, monkeypatch):
    """补救任务可改负责人；改标题/阶段 → 403。"""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    client.patch(
        f"/api/v1/ge/deviations/{body['deviation']['id']}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    graph2 = get_graph(client, created["id"], U_PM)
    remediation = next(t for t in graph2["phases"][1]["tasks"] if t.get("is_remediation"))
    rem_id = remediation["id"]
    orig_title = remediation["title"]
    orig_phase = remediation["phase_id"]

    bad_title = client.patch(
        f"/api/v1/ge/tasks/{rem_id}",
        headers=jwt_headers(U_PM),
        json={"title": "篡改补救标题"},
    )
    assert bad_title.status_code == 403
    assert bad_title.json()["detail"] == "remediation_task_fields_immutable"

    other_phase = next(p["id"] for p in graph2["phases"] if p["id"] != orig_phase)
    bad_phase = client.patch(
        f"/api/v1/ge/tasks/{rem_id}",
        headers=jwt_headers(U_PM),
        json={"phase_id": other_phase},
    )
    assert bad_phase.status_code == 403

    ok = client.patch(
        f"/api/v1/ge/tasks/{rem_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_ZHANGSAN},
    )
    assert ok.status_code == 200, ok.text
    graph3 = get_graph(client, created["id"], U_PM)
    rem2 = next(t for ph in graph3["phases"] for t in ph["tasks"] if t["id"] == rem_id)
    assert rem2["assignee_user_id"] == U_ZHANGSAN
    assert rem2["title"] == orig_title
    assert rem2["phase_id"] == orig_phase


def test_deviated_task_no_produce_edge(client, monkeypatch):
    """After activate, deviated task has no produce edge."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    client.patch(
        f"/api/v1/ge/deviations/{body['deviation']['id']}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
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
            assert task.get("effective_status") != "deviated"
            assert task.get("status") != "deviated"


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


def test_open_without_produce_409(client):
    """Opening deviation requires an existing produce task."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi = _gi(graph, "诊断报告")
    task_id = task_id_by_title(graph, "编写诊断报告")
    resp_del = client.delete(
        f"/api/v1/ge/tasks/{task_id}/produces/{gi['id']}",
        headers=jwt_headers(U_PM),
    )
    assert resp_del.status_code == 200, resp_del.text
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        resp = client.post(
            f"/api/v1/ge/gate-items/{gi['id']}/deviations/open",
            headers=jwt_headers(U_PM),
            json={"kind": "overdue"},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "deviation_open_requires_produce"


def test_activate_deviation(client, monkeypatch):
    """GE-T72 · activate · planned_due sync · reason/plan optional."""
    pa_calls: list[dict] = []

    def _fake_pa(**kwargs):
        pa_calls.append(kwargs)

    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", _fake_pa)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    dev_id = body["deviation"]["id"]
    missing = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "activate"},
    )
    assert missing.status_code == 400
    assert missing.json()["detail"] == "deviation_activate_incomplete"
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["deviation"]["status"] == "active"
    assert data["gate_item"]["planned_due"] == "2026-06-10"
    assert data["deviation"]["remediation_task_id"]
    assert pa_calls
    assert pa_calls[0]["event"] == "ge.deviation.activated"


def test_open_phase_submit_409(client):
    """GE-T81 · open (no task yet): GI submit 409."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    _open_overdue_deviation(client, graph)
    gi = _gi(get_graph(client, created["id"], U_PM), "诊断报告")
    submit = client.post(
        f"/api/v1/ge/gate-items/{gi['id']}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("补救提交"),
    )
    assert submit.status_code == 409
    assert submit.json()["detail"] == "deviation_not_activated"


def test_system_node_scope_still_403(client):
    """GE-T82 · system GI still cannot open scope deviation."""
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


def test_system_start_overdue_open_then_activate_creates_remediation(client, monkeypatch):
    """Overdue system GI: open allowed; activate creates non-system 补救 task."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM, bootstrap_startup=False)
    bootstrap_golden_phase_schedule(client, created["id"], U_PM)
    graph = get_graph(client, created["id"], U_PM)
    start_phase = phase_by_name(graph, "开始")
    start_gi = next(gi for gi in start_phase["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME)
    start_task = next(t for t in start_phase["tasks"] if t["title"] == SYSTEM_START_TASK_TITLE)
    assert start_gi.get("is_system") is True
    assert start_task.get("is_system") is True
    assert start_gi.get("planned_due"), "system GI needs planned_due to be overdue"
    assert start_gi["id"] in (start_task.get("produces") or [])
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        resp = client.post(
            f"/api/v1/ge/gate-items/{start_gi['id']}/deviations/open",
            headers=jwt_headers(U_PM),
            json={"kind": "overdue"},
        )
    assert resp.status_code == 200, resp.text
    graph2 = get_graph(client, created["id"], U_PM)
    start_phase2 = phase_by_name(graph2, "开始")
    gi2 = next(gi for gi in start_phase2["gate_items"] if gi["id"] == start_gi["id"])
    assert gi2["status"] == "deviation"
    assert gi2["deviation"]["status"] == "open"
    orig = next(t for t in start_phase2["tasks"] if t["id"] == start_task["id"])
    assert orig.get("status") != "deviated"
    assert orig.get("effective_status") != "deviated"
    assert start_gi["id"] in (orig.get("produces") or [])
    act = client.patch(
        f"/api/v1/ge/deviations/{gi2['deviation']['id']}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-01-07"},
    )
    assert act.status_code == 200, act.text
    graph3 = get_graph(client, created["id"], U_PM)
    start_phase3 = phase_by_name(graph3, "开始")
    orig3 = next(t for t in start_phase3["tasks"] if t["id"] == start_task["id"])
    assert orig3["status"] == "deviated"
    assert orig3["produces"] == []
    remediation = next(t for t in start_phase3["tasks"] if t["title"] == f"补救·{SYSTEM_START_GATE_ITEM_NAME}")
    assert remediation.get("is_system") is False
    assert remediation.get("is_remediation") is True
    assert remediation["produces"] == [start_gi["id"]]


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
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    graph2 = get_graph(client, created["id"], U_PM)
    remediation_id = next(t["id"] for phase in graph2["phases"] for t in phase["tasks"] if t.get("is_remediation"))
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


def test_extend_due_only_time_first(client, monkeypatch):
    """Canvas 钟路径：active 后无 extend_reason 可 extend；缺 due → 400。"""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev_id = _open_overdue_deviation(client, graph)["deviation"]["id"]
    client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    missing = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "extend"},
    )
    assert missing.status_code == 400
    assert missing.json()["detail"] == "deviation_activate_incomplete"

    new_due = "2026-06-12"
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "extend", "remediation_due": new_due},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deviation"]["remediation_due"][:10] == new_due
    assert body["deviation"]["revision"] == 1
    gi = body["gate_item"]
    assert (gi.get("planned_due") or "")[:10] == new_due


def test_extend_revision_plan_required(client, monkeypatch):
    """GE-T74 · extend revision and plan required at >=3 when extend_reason present."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    dev_id = _open_overdue_deviation(client, graph)["deviation"]["id"]
    client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    for i, due in enumerate(("2026-06-12", "2026-06-13"), start=1):
        resp = client.patch(
            f"/api/v1/ge/deviations/{dev_id}",
            headers=jwt_headers(U_PM),
            json={
                "action": "extend",
                "remediation_due": due,
                "extend_reason": f"延期{i}",
            },
        )
        assert resp.status_code == 200, resp.text
    bad = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "extend",
            "remediation_due": "2026-06-14",
            "extend_reason": "need plan",
        },
    )
    assert bad.status_code == 400
    # 钟路径 time_first：revision>=3 仍可仅 due 改期
    clock_ok = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "extend", "remediation_due": "2026-06-14"},
    )
    assert clock_ok.status_code == 200, clock_ok.text
    assert clock_ok.json()["deviation"]["revision"] == 3
    ok = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={
            "action": "extend",
            "remediation_due": "2026-06-15",
            "extend_reason": "need plan",
            "remediation_plan": "updated plan",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["deviation"]["revision"] == 4


def test_cancel_snapshot_rollback(client):
    """GE-T79 · cancel restores produce and statuses."""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    orig_task = next(t for t in graph["phases"][1]["tasks"] if t["title"] == "编写诊断报告")
    orig_gi_status = _gi(graph, "诊断报告")["status"]
    dev_id = _open_overdue_deviation(client, graph)["deviation"]["id"]
    resp = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PM),
        json={"action": "cancel", "cancel_reason": "方案变更"},
    )
    assert resp.status_code == 200, resp.text
    graph2 = get_graph(client, created["id"], U_PM)
    gi = _gi(graph2, "诊断报告")
    assert gi["status"] in (orig_gi_status, "draft", "rejected")
    task = next(t for t in graph2["phases"][1]["tasks"] if t["title"] == "编写诊断报告")
    assert task.get("effective_status") != "deviated"
    assert task.get("status") != "deviated"
    assert gi["id"] in task["produces"]
    detail = client.get(f"/api/v1/ge/deviations/{dev_id}", headers=jwt_headers(U_PM))
    assert detail.json()["status"] == "cancelled"


def test_deviation_produce_immutable_on_unlink(client, monkeypatch):
    """GE-T87 · active deviation: remediation produce cannot be removed manually."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    client.patch(
        f"/api/v1/ge/deviations/{body['deviation']['id']}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
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


def test_deviated_task_patch_immutable(client, monkeypatch):
    """GE-T88 · deviated task cannot be patched."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    client.patch(
        f"/api/v1/ge/deviations/{body['deviation']['id']}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    graph2 = get_graph(client, created["id"], U_PM)
    deviated = next(
        t for t in graph2["phases"][1]["tasks"]
        if t.get("status") == "deviated" or t.get("effective_status") == "deviated"
    )
    resp = client.patch(
        f"/api/v1/ge/tasks/{deviated['id']}",
        headers=jwt_headers(U_PM),
        json={"title": "不应成功"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "task_deviated_immutable"


def test_remediation_task_not_deletable(client, monkeypatch):
    """GE-T89 · remediation / deviated tasks cannot be deleted."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    body = _open_overdue_deviation(client, graph)
    client.patch(
        f"/api/v1/ge/deviations/{body['deviation']['id']}",
        headers=jwt_headers(U_PM),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    graph2 = get_graph(client, created["id"], U_PM)
    remediation = next(t for t in graph2["phases"][1]["tasks"] if t.get("is_remediation"))
    deviated = next(
        t for t in graph2["phases"][1]["tasks"]
        if t.get("status") == "deviated" or t.get("effective_status") == "deviated"
    )
    rem_resp = client.delete(f"/api/v1/ge/tasks/{remediation['id']}", headers=jwt_headers(U_PM))
    assert rem_resp.status_code == 409
    assert rem_resp.json()["detail"] == "remediation_task_not_deletable"
    dev_resp = client.delete(f"/api/v1/ge/tasks/{deviated['id']}", headers=jwt_headers(U_PM))
    assert dev_resp.status_code == 409
    assert dev_resp.json()["detail"] == "task_deviated_immutable"
