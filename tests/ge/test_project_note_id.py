"""M19 · project_note_id schema projection (PR-1)."""

from __future__ import annotations

import uuid

from tests.conftest import jwt_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, create_project, get_graph


def test_create_project_with_project_note_id(client):
    note_id = str(uuid.uuid4())
    body = {**GOLDEN_PROJECT_BODY, "project_note_id": note_id}
    created = create_project(client, U_PM, body)
    assert created["project_note_id"] == note_id

    project_id = created["id"]
    get_resp = client.get(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_PM),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["project_note_id"] == note_id

    graph = get_graph(client, project_id, U_PM)
    assert graph["project"]["project_note_id"] == note_id


def test_create_project_without_project_note_id_nullable(client):
    body = {**GOLDEN_PROJECT_BODY}
    body["project_note_id"] = None
    created = create_project(client, U_PM, body)
    assert created.get("project_note_id") is None

    list_resp = client.get("/api/v1/ge/projects", headers=jwt_headers(U_PM))
    assert list_resp.status_code == 200
    row = next(p for p in list_resp.json() if p["id"] == created["id"])
    assert row["project_note_id"] is None


def test_patch_project_returns_project_note_id(client):
    note_id = str(uuid.uuid4())
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "project_note_id": note_id})
    resp = client.patch(
        f"/api/v1/ge/projects/{created['id']}",
        headers=jwt_headers(U_PM),
        json={"name": "改名后"},
    )
    assert resp.status_code == 200
    assert resp.json()["project_note_id"] == note_id
