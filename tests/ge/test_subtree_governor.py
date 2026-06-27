"""GE-T90 subtree_governor read + structural write · M24 steward full govern (GE-T101/102)."""

from __future__ import annotations

from app.constants import GE_DEFAULT_OBJECTIVE_ID, GE_DEFAULT_PROGRAM_ID, GE_DEFAULT_SUB_OBJECTIVE_ID
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_PM,
    U_STRANGER,
    U_ZHANGSAN,
    create_project,
    get_graph,
    material_submit_payload,
    task_id_by_title,
)

U_OWNER = "u-owner"
U_GOVERNOR = "u-governor"


def _patch_objective_owner(client, objective_id: str, owner_user_id: str) -> None:
    resp = client.patch(
        f"/api/v1/ge/objectives/{objective_id}",
        headers=service_headers("reviewer-1"),
        json={"owner_user_id": owner_user_id},
    )
    assert resp.status_code == 200, resp.text


def _gate_item_id(graph, name: str) -> str:
    for phase in graph["phases"]:
        for gi in phase["gate_items"]:
            if gi["name"] == name:
                return gi["id"]
    raise AssertionError(f"gate item {name!r} not found")


def test_company_owner_reads_non_participant_project(client):
    _patch_objective_owner(client, GE_DEFAULT_OBJECTIVE_ID, U_OWNER)
    created = create_project(client, U_PM)
    project_id = created["id"]

    owner_list = client.get("/api/v1/ge/projects", headers=jwt_headers(U_OWNER))
    assert owner_list.status_code == 200
    assert project_id in {p["id"] for p in owner_list.json()}

    owner_detail = client.get(f"/api/v1/ge/projects/{project_id}", headers=jwt_headers(U_OWNER))
    assert owner_detail.status_code == 200

    owner_graph = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_OWNER))
    assert owner_graph.status_code == 200
    assert owner_graph.json()["graph_editable"] is True

    stranger = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_STRANGER))
    assert stranger.status_code == 403


def test_governor_program_projects_full_list(client):
    _patch_objective_owner(client, GE_DEFAULT_OBJECTIVE_ID, U_OWNER)
    created = create_project(client, U_PM)
    program_id = created["program_id"]

    resp = client.get(f"/api/v1/ge/programs/{program_id}", headers=jwt_headers(U_OWNER))
    assert resp.status_code == 200
    assert created["id"] in {p["id"] for p in resp.json()["projects"]}

    stranger = client.get(f"/api/v1/ge/programs/{program_id}", headers=jwt_headers(U_STRANGER))
    assert stranger.status_code == 200
    assert created["id"] not in {p["id"] for p in stranger.json()["projects"]}


def test_governor_structural_patch_and_canvas_write_allowed(client):
    """GE-T101 · steward can PATCH graph."""
    _patch_objective_owner(client, GE_DEFAULT_OBJECTIVE_ID, U_OWNER)
    created = create_project(client, U_PM)
    project_id = created["id"]

    patch = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_OWNER),
        json={"name": "owner-renamed"},
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "owner-renamed"

    graph_resp = client.get(f"/api/v1/ge/projects/{project_id}/graph", headers=jwt_headers(U_OWNER))
    assert graph_resp.status_code == 200
    graph = graph_resp.json()
    assert graph["graph_editable"] is True

    task_id = task_id_by_title(graph, "编写诊断报告")
    patch_task = client.patch(
        f"/api/v1/ge/tasks/{task_id}",
        headers=jwt_headers(U_OWNER),
        json={"title": "负责人改标题"},
    )
    assert patch_task.status_code == 200, patch_task.text


def test_steward_non_pm_can_patch_name_and_pm(client):
    """GE-T102 · steward PATCH name/pm (project activate endpoint removed)."""
    _patch_objective_owner(client, GE_DEFAULT_OBJECTIVE_ID, U_OWNER)
    created = create_project(client, U_PM)
    project_id = created["id"]

    patch_name = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_OWNER),
        json={"name": "steward-renamed"},
    )
    assert patch_name.status_code == 200
    assert patch_name.json()["name"] == "steward-renamed"

    patch_pm = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_OWNER),
        json={"pm_user_id": U_ZHANGSAN},
    )
    assert patch_pm.status_code == 200
    assert patch_pm.json()["pm_user_id"] == U_ZHANGSAN


def test_steward_can_proxy_submit_and_sign(client):
    """GE-T101 extension · steward execution write."""
    _patch_objective_owner(client, GE_DEFAULT_OBJECTIVE_ID, U_OWNER)
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    gi_x = _gate_item_id(graph, "诊断报告")

    submit = client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_OWNER),
        json=material_submit_payload("负责人代提交"),
    )
    assert submit.status_code == 200, submit.text

    sign = client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_OWNER))
    assert sign.status_code == 200, sign.text


def test_non_default_program_create_requires_governor(client):
    create_prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "战略项目群",
            "objective_id": GE_DEFAULT_SUB_OBJECTIVE_ID,
            "owner_user_id": U_GOVERNOR,
        },
    )
    assert create_prog.status_code == 201
    program_id = create_prog.json()["id"]

    body = {**GOLDEN_PROJECT_BODY, "program_id": program_id}
    forbidden = client.post("/api/v1/ge/projects", headers=jwt_headers(U_STRANGER), json=body)
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "not_subtree_governor"

    allowed = client.post("/api/v1/ge/projects", headers=jwt_headers(U_GOVERNOR), json=body)
    assert allowed.status_code == 201


def test_ancestor_owner_governs_nested_program(client):
    _patch_objective_owner(client, GE_DEFAULT_OBJECTIVE_ID, U_OWNER)
    create_prog = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": "子树项目群",
            "objective_id": GE_DEFAULT_SUB_OBJECTIVE_ID,
            "owner_user_id": "u-other",
        },
    )
    assert create_prog.status_code == 201
    program_id = create_prog.json()["id"]

    body = {**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": U_PM}
    created = client.post("/api/v1/ge/projects", headers=jwt_headers(U_OWNER), json=body)
    assert created.status_code == 201
    project_id = created.json()["id"]

    patch = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_OWNER),
        json={"name": "祖先-owner-改名"},
    )
    assert patch.status_code == 200
