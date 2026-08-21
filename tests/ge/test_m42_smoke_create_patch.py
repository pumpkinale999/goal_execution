"""M42 smoke: create/patch must reject dirty Person ids (no wecom:/short names)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.ge_person_id import require_person_user_id
from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, create_project, ensure_formal_test_program


def _detail(resp) -> str:
    body = resp.json()
    d = body.get("detail", body)
    if isinstance(d, dict):
        return str(d.get("detail") or "")
    return str(d)


@pytest.mark.parametrize("dirty", ["wecom:yinyumei", "victor", "system"])
def test_m42_smoke_create_project_rejects_dirty_pm(client, dirty: str):
    program_id = ensure_formal_test_program(client)
    r = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers(U_PM),
        json={
            "name": "M42 smoke dirty pm",
            "pm_user_id": dirty,
            "program_id": program_id,
            "lifecycle_start": "2026-01-01",
            "lifecycle_end": "2026-12-31",
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    assert r.status_code == 400
    assert _detail(r) == "invalid_person_user_id"


def test_m42_smoke_create_project_accepts_numeric_pm(client):
    created = create_project(client, U_PM)
    assert created["pm_user_id"] == U_PM
    assert str(created["pm_user_id"]).isdigit()


def test_m42_smoke_patch_pm_rejects_dirty(client):
    created = create_project(client, U_PM)
    r = client.patch(
        f"/api/v1/ge/projects/{created['id']}",
        headers=jwt_headers(U_PM),
        json={"pm_user_id": "wecom:x"},
    )
    assert r.status_code == 400
    assert _detail(r) == "invalid_person_user_id"


def test_m42_smoke_helper_contract():
    with pytest.raises(HTTPException) as ei:
        require_person_user_id("wecom:x")
    assert ei.value.detail == {"detail": "invalid_person_user_id"}
    assert require_person_user_id(U_PM) == U_PM
