"""GE-T07 · GE-T08 · GE-T14 create/delete tests."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_CREATOR,
    U_PM,
    U_STRANGER,
    U_ZHANGSAN,
    create_project,
    ensure_formal_test_program,
    get_graph,
)


def test_orphan_signer_400(client):
    program_id = ensure_formal_test_program(client)
    body = {
        "name": "bad",
        "pm_user_id": U_PM,
        "program_id": program_id,
        "phases": [
            {
                "sequence": 1,
                "name": "P1",
                "gate_items": [{"key": "X", "name": "X", "form": "material"}],
                "tasks": [
                    {
                        "key": "A",
                        "title": "A",
                        "assignee_user_id": U_ZHANGSAN,
                        "produces": ["X"],
                    }
                ],
            }
        ],
    }
    resp = client.post("/api/v1/ge/projects", headers=jwt_headers(U_PM), json=body)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "gate_item_orphan_signer"


def test_create_project_requires_program_id(client):
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(U_PM),
        json={**GOLDEN_PROJECT_BODY, "program_id": None},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "program_id_required"


def test_create_project_with_formal_program(client):
    program_id = ensure_formal_test_program(client)
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "program_id": program_id})
    assert created["program_id"] == program_id
    assert created["status"] == "active"


def test_delete_empty_by_pm_or_reviewer(client):
    """GE-T58 · GE-T59"""
    empty_body = {
        "name": "空项目",
        "pm_user_id": U_PM,
        "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
    }
    created = create_project(client, U_PM, empty_body, bootstrap_startup=False)
    project_id = created["id"]
    deny_creator = client.delete(f"/api/v1/ge/projects/{project_id}", headers=jwt_headers(U_CREATOR))
    assert deny_creator.status_code == 403
    assert deny_creator.json()["detail"] == "not_project_governor"
    ok_pm = client.delete(f"/api/v1/ge/projects/{project_id}", headers=jwt_headers(U_PM))
    assert ok_pm.status_code == 204


def test_reviewer_service_token_can_delete_empty_project(client):
    from tests.conftest import service_headers

    empty_body = {
        "name": "评审员可删",
        "pm_user_id": U_PM,
        "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
    }
    created = create_project(client, U_PM, empty_body, bootstrap_startup=False)
    project_id = created["id"]
    ok = client.delete(f"/api/v1/ge/projects/{project_id}", headers=service_headers("reviewer-1"))
    assert ok.status_code == 204


def test_creator_read_not_pm(client):
    program_id = ensure_formal_test_program(client, owner_user_id=U_CREATOR)
    body = {**GOLDEN_PROJECT_BODY, "pm_user_id": U_PM, "program_id": program_id}
    created = create_project(client, U_CREATOR, body)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_CREATOR)
    assert graph["project"]["status"] == "active"
