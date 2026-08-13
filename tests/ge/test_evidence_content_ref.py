"""GE-T200～T207 · GateItem evidence content_ref (fake NoteProjectGuard · M2)."""

from __future__ import annotations

import uuid

from app.services.ge_content_ref_migration import plan_content_ref_backfill
from app.services.ge_note_project_guard import (
    MappingNoteProjectGuard,
    UnavailableNoteProjectGuard,
    set_note_project_guard,
)
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    TEST_PROJECT_NOTE_ID,
    U_LISI,
    U_PM,
    U_WANGWU,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    phase_by_name,
    structured_submit_payload,
    task_id_by_title,
)

CHILD_NOTE_ID = "b0000000-0000-4000-8000-000000000002"
FOREIGN_NOTE_ID = "c0000000-0000-4000-8000-000000000003"


def _detail(resp) -> str:
    body = resp.json()
    detail = body.get("detail", body)
    if isinstance(detail, dict):
        return str(detail.get("detail", detail))
    return str(detail)


def _start_material(client, graph):
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    return gi_x


def test_ge_t200_missing_content_ref_no_server_fill(client):
    """三类缺 content_ref → 400（有根亦不服务端填）。"""
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    assert graph["project"]["project_note_id"] == TEST_PROJECT_NOTE_ID
    gi_x = _start_material(client, graph)
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json={"payload": {"summary": "有根但未显式 ref"}},
    )
    assert resp.status_code == 400
    assert _detail(resp) == "invalid_content_ref"

    project_id = created["id"]
    dev = phase_by_name(graph, "开发")
    metric = client.post(
        f"/api/v1/ge/projects/{project_id}/phases/{dev['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "T200指标", "form": "metric", "target_value": 1, "operator": ">=", "planned_due": "2026-06-18"},
    )
    assert metric.status_code == 200
    gi_m = next(
        gi["id"]
        for phase in metric.json()["phases"]
        for gi in phase["gate_items"]
        if gi["name"] == "T200指标"
    )
    task_b = task_id_by_title(get_graph(client, project_id, U_PM), "编写接口规格")
    client.post(f"/api/v1/ge/tasks/{task_b}/produces", headers=jwt_headers(U_PM), json={"gate_item_id": gi_m})
    client.post(f"/api/v1/ge/tasks/{task_b}/start", headers=jwt_headers(U_LISI))
    miss_metric = client.post(
        f"/api/v1/ge/gate-items/{gi_m}/submit",
        headers=jwt_headers(U_LISI),
        json={"payload": {"actual_value": 2, "summary": "ok"}},
    )
    assert miss_metric.status_code == 400
    assert _detail(miss_metric) == "invalid_content_ref"


def test_ge_t201_foreign_and_fragment(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    project_id = created["id"]
    gi_x = _start_material(client, graph)

    set_note_project_guard(
        MappingNoteProjectGuard(
            {
                (project_id, TEST_PROJECT_NOTE_ID): "ok",
                (project_id, FOREIGN_NOTE_ID): "not_in_tree",
            },
            default="not_in_tree",
        )
    )
    foreign = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("x", project_note_id=FOREIGN_NOTE_ID),
    )
    assert foreign.status_code == 400
    assert _detail(foreign) == "note_not_in_project"

    frag = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json={"payload": {"summary": "x", "content_ref": f"kb:{TEST_PROJECT_NOTE_ID}#a"}},
    )
    assert frag.status_code == 400
    assert _detail(frag) == "invalid_content_ref"


def test_ge_t202_child_note_including_dir(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    project_id = created["id"]
    gi_x = _start_material(client, graph)
    set_note_project_guard(
        MappingNoteProjectGuard({(project_id, CHILD_NOTE_ID): "ok"}, default="not_in_tree")
    )
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("child ok", project_note_id=CHILD_NOTE_ID),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["gate_item"]["payload"]["content_ref"] == f"kb:{CHILD_NOTE_ID}"


def test_ge_t203_no_root_and_binding_missing(client):
    created = create_project(
        client, U_PM, {**GOLDEN_PROJECT_BODY, "project_note_id": None}, bootstrap_startup=False
    )
    graph = get_graph(client, created["id"], U_PM)
    gi_x = _start_material(client, graph)
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("x"),
    )
    assert resp.status_code == 409
    assert _detail(resp) == "project_note_required"

    created2 = create_project(client, U_PM)
    graph2 = get_graph(client, created2["id"], U_PM)
    project_id = created2["id"]
    gi2 = _start_material(client, graph2)
    set_note_project_guard(
        MappingNoteProjectGuard(
            {(project_id, TEST_PROJECT_NOTE_ID): "project_binding_missing"},
            default="project_binding_missing",
        )
    )
    bind = client.post(
        f"/api/v1/ge/gate-items/{gi2}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("x"),
    )
    assert bind.status_code == 400
    assert _detail(bind) == "project_binding_missing"


def test_ge_t204_immutable_rebinding_and_migration_keep(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi_x = _start_material(client, graph)
    submit = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("done"),
    )
    assert submit.status_code == 200
    patch = client.patch(
        f"/api/v1/ge/gate-items/{gi_x}",
        headers=jwt_headers(U_PM),
        json={"content_ref": f"kb:{CHILD_NOTE_ID}"},
    )
    assert patch.status_code == 400
    assert _detail(patch) == "content_ref_immutable"

    sign = client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_WANGWU))
    # 方案 phase may not have wangwu as signer — use eligible from produce chain
    # After X submit, signer is via task C prerequisites on Y typically; for X need a prereq task.
    # Golden: only B has prereq X — Lisi signs? eligible_signers from prereq tasks.
    if sign.status_code != 200:
        sign = client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))
    assert sign.status_code == 200, sign.text
    patch2 = client.patch(
        f"/api/v1/ge/gate-items/{gi_x}",
        headers=jwt_headers(U_PM),
        json={"content_ref": f"kb:{CHILD_NOTE_ID}"},
    )
    assert patch2.status_code == 400
    assert _detail(patch2) == "content_ref_immutable"

    kept, reason = plan_content_ref_backfill(
        {"summary": "x", "content_ref": "https://example.com/a"},
        project_note_id=TEST_PROJECT_NOTE_ID,
        status="signed",
    )
    assert kept is None and reason == "keep_existing"
    filled, reason2 = plan_content_ref_backfill(
        {"summary": "x"},
        project_note_id=TEST_PROJECT_NOTE_ID,
    )
    assert reason2 == "filled_root"
    assert filled["content_ref"] == f"kb:{TEST_PROJECT_NOTE_ID}"
    again, reason3 = plan_content_ref_backfill(filled, project_note_id=TEST_PROJECT_NOTE_ID)
    assert again is None and reason3 == "keep_existing"


def test_ge_t205_kb_unavailable_no_degrade(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    gi_x = _start_material(client, graph)
    set_note_project_guard(UnavailableNoteProjectGuard())
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("x"),
    )
    assert resp.status_code == 503
    assert _detail(resp) == "note_validation_unavailable"


def test_ge_t206_trash_unavailable_submit_and_sign(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    project_id = created["id"]
    gi_x = _start_material(client, graph)
    set_note_project_guard(
        MappingNoteProjectGuard({(project_id, TEST_PROJECT_NOTE_ID): "unavailable"}, default="unavailable")
    )
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("x"),
    )
    assert resp.status_code == 400
    assert _detail(resp) == "content_ref_note_unavailable"

    # Accept for submit then trash for sign
    set_note_project_guard(MappingNoteProjectGuard({(project_id, TEST_PROJECT_NOTE_ID): "ok"}))
    ok = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("ok"),
    )
    assert ok.status_code == 200
    set_note_project_guard(
        MappingNoteProjectGuard({(project_id, TEST_PROJECT_NOTE_ID): "not_found"}, default="not_found")
    )
    sign = client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))
    assert sign.status_code == 400
    assert _detail(sign) == "content_ref_note_unavailable"


def test_ge_t207_batch_create_metric_status_with_ref(client):
    child = str(uuid.uuid4())
    body = {
        **GOLDEN_PROJECT_BODY,
        "phases": [
            {
                "sequence": 1,
                "name": "方案",
                "gate_items": [
                    {
                        "key": "M",
                        "name": "批量指标",
                        "form": "metric",
                        "target_value": 10,
                        "operator": ">=",
                        "planned_due": "2026-06-10",
                        "content_ref": f"kb:{TEST_PROJECT_NOTE_ID}",
                    },
                    {
                        "key": "S",
                        "name": "批量状态",
                        "form": "status",
                        "target_state": "就绪",
                        "target_value": True,
                        "planned_due": "2026-06-11",
                        "content_ref": f"kb:{child}",
                    },
                ],
                "tasks": [
                    {
                        "key": "A",
                        "title": "产出指标",
                        "assignee_user_id": U_ZHANGSAN,
                        "produces": ["M"],
                    },
                    {
                        "key": "B",
                        "title": "产出状态",
                        "assignee_user_id": U_LISI,
                        "produces": ["S"],
                        "prerequisites": ["M"],
                    },
                    {
                        "key": "C",
                        "title": "签收状态",
                        "assignee_user_id": U_WANGWU,
                        "prerequisites": ["S"],
                    },
                ],
            }
        ],
    }
    created = create_project(client, U_PM, body, seed_schedule=False)
    graph = get_graph(client, created["id"], U_PM)
    names = {
        gi["name"]: gi
        for phase in graph["phases"]
        for gi in phase["gate_items"]
        if not gi.get("is_system")
    }
    assert names["批量指标"]["form"] == "metric"
    assert names["批量指标"]["payload"]["content_ref"] == f"kb:{TEST_PROJECT_NOTE_ID}"
    assert names["批量状态"]["form"] == "status"
    assert names["批量状态"]["payload"]["content_ref"] == f"kb:{child}"
