"""GE-T50 · bind project_note_id for legacy backfill."""

from __future__ import annotations

import uuid

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import GOLDEN_PROJECT_BODY, U_PM, create_project


def test_service_bind_project_note_success(client):
    body = {**GOLDEN_PROJECT_BODY, "project_note_id": None}
    created = create_project(client, U_PM, body)
    note_id = str(uuid.uuid4())

    resp = client.patch(
        f"/api/v1/ge/projects/{created['id']}/project-note",
        headers=service_headers(U_PM),
        json={"project_note_id": note_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["project_note_id"] == note_id

    get_resp = client.get(
        f"/api/v1/ge/projects/{created['id']}",
        headers=jwt_headers(U_PM),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["project_note_id"] == note_id


def test_service_bind_rejects_when_already_bound(client):
    note_id = str(uuid.uuid4())
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "project_note_id": note_id})

    resp = client.patch(
        f"/api/v1/ge/projects/{created['id']}/project-note",
        headers=service_headers(U_PM),
        json={"project_note_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert (detail["detail"] if isinstance(detail, dict) else detail) == "project_note_already_bound"


def test_jwt_bind_project_note_forbidden(client):
    created = create_project(client, U_PM, {**GOLDEN_PROJECT_BODY, "project_note_id": None})

    resp = client.patch(
        f"/api/v1/ge/projects/{created['id']}/project-note",
        headers=jwt_headers(U_PM),
        json={"project_note_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert (detail["detail"] if isinstance(detail, dict) else detail) == "service_token_required"
