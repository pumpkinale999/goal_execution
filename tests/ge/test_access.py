"""GE-T06 · GE-T10 · GE-T15 access tests."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_LISI,
    U_PM,
    U_STRANGER,
    U_ZHANGSAN,
    create_project,
    get_graph,
)


def test_non_participant_graph_403(client):
    created = create_project(client, U_PM)
    resp = client.get(
        f"/api/v1/ge/projects/{created['id']}/graph",
        headers=jwt_headers(U_STRANGER),
    )
    assert resp.status_code == 403


def test_jwt_project_list_participant_filter(client):
    created = create_project(client, U_PM)
    visible = client.get("/api/v1/ge/projects", headers=jwt_headers(U_ZHANGSAN))
    assert visible.status_code == 200
    ids = {p["id"] for p in visible.json()}
    assert created["id"] in ids
    hidden = client.get("/api/v1/ge/projects", headers=jwt_headers(U_STRANGER))
    assert created["id"] not in {p["id"] for p in hidden.json()}


def test_service_lists_all_projects(client):
    created = create_project(client, U_PM)
    resp = client.get("/api/v1/ge/projects", headers=service_headers("reviewer"))
    assert resp.status_code == 200
    assert created["id"] in {p["id"] for p in resp.json()}


def test_program_projects_participant_filter(client):
    created = create_project(client, U_PM)
    program_id = created["program_id"]
    participant = client.get(f"/api/v1/ge/programs/{program_id}", headers=jwt_headers(U_ZHANGSAN))
    assert participant.status_code == 200
    assert created["id"] in {p["id"] for p in participant.json()["projects"]}
    stranger = client.get(f"/api/v1/ge/programs/{program_id}", headers=jwt_headers(U_STRANGER))
    assert created["id"] not in {p["id"] for p in stranger.json()["projects"]}
    reviewer = client.get(f"/api/v1/ge/programs/{program_id}", headers=service_headers("reviewer"))
    assert created["id"] in {p["id"] for p in reviewer.json()["projects"]}
