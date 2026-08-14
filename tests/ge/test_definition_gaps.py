"""GET …/definition-gaps + graph.definition_gaps (PRA SenseEvent-shaped)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.ge_assess_definition import assess_definition_gaps_from_graph
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_PM,
    U_STRANGER,
    U_ZHANGSAN,
    create_project,
    get_graph,
    phase_by_name,
)


def _minimal_ok_graph() -> dict:
    return {
        "project": {
            "id": "p1",
            "name": "Demo",
            "status": "active",
            "pm_user_id": U_PM,
        },
        "phases": [
            {
                "id": "ph-start",
                "name": "开始",
                "is_system": True,
                "planned_start": "2026-01-01",
                "planned_end": "2026-01-07",
                "gate_items": [
                    {"id": "gi-start", "name": "团队共识", "planned_due": "2026-01-07", "is_system": True}
                ],
                "tasks": [
                    {
                        "id": "t-start",
                        "title": "启动项目",
                        "is_system": True,
                        "assignee_user_id": U_PM,
                        "produces": ["gi-start"],
                    },
                    # 业务任务签收「项目启动」（可有可无；orphan 例外不强制）
                    {
                        "id": "t-biz-from-start",
                        "title": "启动后调研",
                        "is_system": False,
                        "assignee_user_id": U_ZHANGSAN,
                        "produces": [],
                        "prerequisites": ["gi-start"],
                    },
                ],
            },
            {
                "id": "ph-biz",
                "name": "方案",
                "is_system": False,
                "planned_start": "2026-06-01",
                "planned_end": "2026-06-15",
                "gate_items": [
                    {"id": "gi-x", "name": "诊断报告", "planned_due": "2026-06-10"}
                ],
                "tasks": [
                    {
                        "id": "t-a",
                        "title": "编写诊断报告",
                        "is_system": False,
                        "assignee_user_id": U_ZHANGSAN,
                        "produces": ["gi-x"],
                    }
                ],
            },
            {
                "id": "ph-end",
                "name": "结束",
                "is_system": True,
                "planned_start": "2026-12-01",
                "planned_end": "2026-12-07",
                "gate_items": [
                    {"id": "gi-end", "name": "团队复盘", "planned_due": "2026-12-07", "is_system": True}
                ],
                "tasks": [
                    {
                        "id": "t-end",
                        "title": "结项复盘",
                        "is_system": True,
                        "assignee_user_id": U_PM,
                        "produces": ["gi-end"],
                    },
                    {
                        "id": "t-sign",
                        "title": "确认结项",
                        "is_system": True,
                        "assignee_user_id": U_PM,
                        "produces": [],
                        "prerequisites": ["gi-end"],
                    },
                    # 签收业务门控「诊断报告」
                    {
                        "id": "t-sign-x",
                        "title": "审诊断报告",
                        "is_system": False,
                        "assignee_user_id": U_PM,
                        "produces": [],
                        "prerequisites": ["gi-x"],
                    },
                ],
            },
        ],
    }


def test_assess_ok_graph_empty():
    assert assess_definition_gaps_from_graph(_minimal_ok_graph()) == []


def test_assess_start_window_and_project_envelope():
    g = _minimal_ok_graph()
    g["phases"][0]["planned_start"] = None
    g["phases"][0]["planned_end"] = None
    gaps = assess_definition_gaps_from_graph(g)
    types_keys = {(x["type"], x["concern_key"]) for x in gaps}
    assert ("definition.missing_deadline", "pra:def:due:stage:ph-start") in types_keys
    assert ("definition.missing_deadline", "pra:def:due:project:p1") in types_keys
    start_gap = next(x for x in gaps if x["concern_key"] == "pra:def:due:stage:ph-start")
    assert start_gap["message"] == "开始阶段计划窗口未齐"
    assert start_gap["evidence"]["entity_kind"] == "stage"


def test_assess_business_stage_end_and_gate_due_and_producer():
    g = _minimal_ok_graph()
    g["phases"][1]["planned_end"] = None
    g["phases"][1]["gate_items"][0]["planned_due"] = None
    g["phases"][1]["tasks"][0]["produces"] = []
    gaps = assess_definition_gaps_from_graph(g)
    keys = {x["concern_key"] for x in gaps}
    assert "pra:def:due:stage:ph-biz" in keys
    assert "pra:def:due:gate:gi-x" in keys
    assert "pra:def:stage:ph-biz:gate:gi-x" in keys


def test_assess_missing_assignee_and_system_uses_pm():
    g = _minimal_ok_graph()
    g["phases"][1]["tasks"][0]["assignee_user_id"] = ""
    g["phases"][0]["tasks"][0]["assignee_user_id"] = ""  # system start → PM fills
    gaps = assess_definition_gaps_from_graph(g)
    assignee = [x for x in gaps if x["type"] == "definition.missing_assignee"]
    assert len(assignee) == 1
    assert assignee[0]["concern_key"] == "pra:def:assignee:task:t-a"


def test_assess_skips_cancelled():
    g = _minimal_ok_graph()
    g["project"]["status"] = "cancelled"
    g["phases"][0]["planned_start"] = None
    assert assess_definition_gaps_from_graph(g) == []


def test_assess_missing_signer_route_on_business_gate():
    g = _minimal_ok_graph()
    # Drop the consumer of gi-x
    g["phases"][2]["tasks"] = [t for t in g["phases"][2]["tasks"] if t["id"] != "t-sign-x"]
    gaps = assess_definition_gaps_from_graph(g)
    signer = [x for x in gaps if x["concern_key"] == "pra:def:signer:gate:gi-x"]
    assert len(signer) == 1
    assert signer[0]["evidence"]["missing"] == "signer_route"
    assert "签收路由" in signer[0]["message"]


def test_assess_start_gate_orphan_allowed():
    g = _minimal_ok_graph()
    # Remove start sign-route consumer; 项目启动 still OK
    g["phases"][0]["tasks"] = [t for t in g["phases"][0]["tasks"] if t["id"] != "t-biz-from-start"]
    gaps = assess_definition_gaps_from_graph(g)
    assert not any(x["concern_key"] == "pra:def:signer:gate:gi-start" for x in gaps)


def test_assess_end_gate_needs_signer_route():
    g = _minimal_ok_graph()
    g["phases"][2]["tasks"] = [t for t in g["phases"][2]["tasks"] if t["id"] != "t-sign"]
    gaps = assess_definition_gaps_from_graph(g)
    assert any(x["concern_key"] == "pra:def:signer:gate:gi-end" for x in gaps)


def test_assess_eligible_signers_field_counts():
    g = _minimal_ok_graph()
    g["phases"][2]["tasks"] = [t for t in g["phases"][2]["tasks"] if t["id"] != "t-sign-x"]
    g["phases"][1]["gate_items"][0]["eligible_signers"] = [U_PM]
    assert assess_definition_gaps_from_graph(g) == []


def test_definition_gaps_api_auth_and_empty_golden(client: TestClient):
    created = create_project(client, U_PM)
    pid = created["id"]
    resp = client.get(
        f"/api/v1/ge/projects/{pid}/definition-gaps",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["project_id"] == pid
    assert body["gap_count"] == 0
    assert body["gaps"] == []

    denied = client.get(
        f"/api/v1/ge/projects/{pid}/definition-gaps",
        headers=jwt_headers(U_STRANGER),
    )
    assert denied.status_code == 403

    missing = client.get(
        "/api/v1/ge/projects/does-not-exist/definition-gaps",
        headers=jwt_headers(U_PM),
    )
    assert missing.status_code == 404


def test_definition_gaps_clear_start_window_on_api(client: TestClient):
    created = create_project(client, U_PM)
    pid = created["id"]
    graph = get_graph(client, pid, U_PM)
    start = phase_by_name(graph, "开始")
    # Clear start window (system phases allow empty window)
    patch = client.patch(
        f"/api/v1/ge/phases/{start['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_start": None, "planned_end": None},
    )
    assert patch.status_code == 200, patch.text

    resp = client.get(
        f"/api/v1/ge/projects/{pid}/definition-gaps",
        headers=jwt_headers(U_PM),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["gap_count"] >= 2
    keys = {g["concern_key"] for g in body["gaps"]}
    assert f"pra:def:due:stage:{start['id']}" in keys
    assert f"pra:def:due:project:{pid}" in keys

    graph2 = get_graph(client, pid, U_PM)
    assert "definition_gaps" in graph2
    assert {g["concern_key"] for g in graph2["definition_gaps"]} == keys


def test_graph_embeds_definition_gaps_on_golden(client: TestClient):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    assert graph.get("definition_gaps") == []
