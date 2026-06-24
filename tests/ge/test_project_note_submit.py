"""GE-T49 · material submit requires project Note content_ref (M19 PR-2)."""

from __future__ import annotations

import uuid

from tests.conftest import jwt_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    TEST_PROJECT_NOTE_ID,
    U_PM,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
    task_id_by_title,
)


def _setup_with_note(client, *, project_note_id: str | None = TEST_PROJECT_NOTE_ID):
    body = {**GOLDEN_PROJECT_BODY, "project_note_id": project_note_id}
    created = create_project(client, U_PM, body)
    graph = get_graph(client, created["id"], U_PM)
    return created["id"], graph


def test_material_submit_without_project_note_id_returns_409(client):
    project_id, graph = _setup_with_note(client, project_note_id=None)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "project_note_required"


def test_material_submit_wrong_content_ref_returns_400(client):
    _, graph = _setup_with_note(client)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    wrong_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report", project_note_id=wrong_id),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_content_ref"


def test_material_submit_with_project_note_content_ref_succeeds(client):
    _, graph = _setup_with_note(client)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    task_a = task_id_by_title(graph, "编写诊断报告")
    client.post(f"/api/v1/ge/tasks/{task_a}/start", headers=jwt_headers(U_ZHANGSAN))
    resp = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report done"),
    )
    assert resp.status_code == 200
    payload = resp.json()["gate_item"]["payload"]
    assert payload["summary"] == "report done"
    assert payload["content_ref"] == f"kb:{TEST_PROJECT_NOTE_ID}"
