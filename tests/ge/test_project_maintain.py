"""GE-T patch project · P2 strategic chain tests."""

from __future__ import annotations

from app.constants import GE_DEFAULT_OBJECTIVE_ID, GE_DEFAULT_PROGRAM_ID, GE_DEFAULT_SUB_OBJECTIVE_ID
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_CREATOR, U_PM, create_project


def test_patch_project_name_by_pm(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    resp = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_PM),
        json={"name": "新名称"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名称"


def test_patch_project_forbidden_non_pm(client):
    created = create_project(client, U_CREATOR, {**GOLDEN_PROJECT_BODY, "pm_user_id": U_PM})
    project_id = created["id"]
    resp = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_CREATOR),
        json={"name": "非法"},
    )
    assert resp.status_code == 403


def test_create_program_requires_objective_id(client):
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "objective_id_required"


def test_create_program_on_company_objective_forbidden(client):
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群", "objective_id": GE_DEFAULT_OBJECTIVE_ID},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "program_requires_sub_objective"


def test_create_and_patch_program(client):
    create = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群", "objective_id": GE_DEFAULT_SUB_OBJECTIVE_ID, "owner_user_id": "u-owner"},
    )
    assert create.status_code == 201
    program_id = create.json()["id"]
    patch = client.patch(
        f"/api/v1/ge/programs/{program_id}",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群（改）"},
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "产品群（改）"


def test_patch_program_to_company_objective_forbidden(client):
    create = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={"name": "产品群", "objective_id": GE_DEFAULT_SUB_OBJECTIVE_ID, "owner_user_id": "u-owner"},
    )
    assert create.status_code == 201
    program_id = create.json()["id"]
    resp = client.patch(
        f"/api/v1/ge/programs/{program_id}",
        headers=service_headers("reviewer-1"),
        json={"objective_id": GE_DEFAULT_OBJECTIVE_ID},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "program_requires_sub_objective"


def test_patch_default_program_name_allowed(client):
    resp = client.patch(
        f"/api/v1/ge/programs/{GE_DEFAULT_PROGRAM_ID}",
        headers=service_headers("reviewer-1"),
        json={"name": "通用项目池"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "通用项目池"
    assert resp.json()["is_default"] is True


def test_patch_default_program_objective_forbidden(client):
    resp = client.patch(
        f"/api/v1/ge/programs/{GE_DEFAULT_PROGRAM_ID}",
        headers=service_headers("reviewer-1"),
        json={"objective_id": GE_DEFAULT_OBJECTIVE_ID},
    )
    assert resp.status_code == 403


def test_patch_default_objective_name_allowed(client):
    resp = client.patch(
        f"/api/v1/ge/objectives/{GE_DEFAULT_OBJECTIVE_ID}",
        headers=service_headers("reviewer-1"),
        json={"name": "让数坤公司成为公众公司"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "让数坤公司成为公众公司"
    assert resp.json()["is_default"] is True


def test_create_sub_objective(client):
    create = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={"name": "2026 增长", "parent_id": GE_DEFAULT_OBJECTIVE_ID, "owner_user_id": "u-owner"},
    )
    assert create.status_code == 201
    assert create.json()["parent_id"] == GE_DEFAULT_OBJECTIVE_ID


def test_delete_sub_objective(client):
    create = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={"name": "待删子目标", "parent_id": GE_DEFAULT_OBJECTIVE_ID, "owner_user_id": "u-owner"},
    )
    assert create.status_code == 201
    obj_id = create.json()["id"]
    deleted = client.delete(f"/api/v1/ge/objectives/{obj_id}", headers=service_headers("reviewer-1"))
    assert deleted.status_code == 204
