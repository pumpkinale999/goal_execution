"""PN-NW-01～06 · K29 per-note write grants (GE)."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import U_PM, U_STRANGER, create_project
from tests.ge.test_project_members import U_MEMBER_2, U_MEMBER_ONLY, _add


NOTE_A = "note-id-alpha"
NOTE_B = "note-id-beta"


def _grants(client, project_id: str, note_id: str, user_id: str = U_PM) -> list[str]:
    resp = client.get(
        f"/api/v1/ge/projects/{project_id}/notes/{note_id}/write-grants",
        headers=jwt_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["user_ids"]


def _put(client, project_id: str, note_id: str, user_ids: list[str], actor: str = U_PM):
    return client.put(
        f"/api/v1/ge/projects/{project_id}/notes/{note_id}/write-grants",
        headers=jwt_headers(actor),
        json={"user_ids": user_ids},
    )


def test_pn_nw_01_put_rejects_non_member(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    resp = _put(client, project_id, NOTE_A, [U_STRANGER])
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "not_project_member"


def test_pn_nw_02_put_replace_idempotent(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    assert _add(client, project_id, U_MEMBER_ONLY, "member").status_code == 201
    assert _add(client, project_id, U_MEMBER_2, "member").status_code == 201

    r1 = _put(client, project_id, NOTE_A, [U_MEMBER_ONLY, U_MEMBER_2])
    assert r1.status_code == 200, r1.text
    assert set(r1.json()["user_ids"]) == {U_MEMBER_ONLY, U_MEMBER_2}

    r2 = _put(client, project_id, NOTE_A, [U_MEMBER_ONLY])
    assert r2.status_code == 200, r2.text
    assert r2.json()["user_ids"] == [U_MEMBER_ONLY]
    assert _grants(client, project_id, NOTE_A) == [U_MEMBER_ONLY]

    r3 = _put(client, project_id, NOTE_A, [U_MEMBER_ONLY])
    assert r3.status_code == 200
    assert r3.json()["user_ids"] == [U_MEMBER_ONLY]


def test_pn_nw_03_delete_member_clears_all_note_grants(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    assert _add(client, project_id, U_MEMBER_ONLY, "member").status_code == 201
    assert _put(client, project_id, NOTE_A, [U_MEMBER_ONLY]).status_code == 200
    assert _put(client, project_id, NOTE_B, [U_MEMBER_ONLY]).status_code == 200
    assert U_MEMBER_ONLY in _grants(client, project_id, NOTE_A)
    assert U_MEMBER_ONLY in _grants(client, project_id, NOTE_B)

    deleted = client.delete(
        f"/api/v1/ge/projects/{project_id}/members/{U_MEMBER_ONLY}",
        headers=jwt_headers(U_PM),
    )
    assert deleted.status_code == 204, deleted.text
    assert _grants(client, project_id, NOTE_A) == []
    assert _grants(client, project_id, NOTE_B) == []


def test_pn_nw_04_delete_project_clears_grants(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    assert _add(client, project_id, U_MEMBER_ONLY, "member").status_code == 201
    assert _put(client, project_id, NOTE_A, [U_MEMBER_ONLY]).status_code == 200
    assert U_MEMBER_ONLY in _grants(client, project_id, NOTE_A)

    deleted = client.delete(
        f"/api/v1/ge/projects/{project_id}",
        headers=service_headers("reviewer-1", is_reviewer=True),
    )
    assert deleted.status_code == 204, deleted.text

    from app.db import session_scope
    from app.models.ge import GeProjectNoteWriteGrant

    with session_scope() as db:
        left = (
            db.query(GeProjectNoteWriteGrant)
            .filter(GeProjectNoteWriteGrant.project_id == project_id)
            .count()
        )
        assert left == 0


def test_pn_nw_05_non_governor_put_forbidden(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    assert _add(client, project_id, U_MEMBER_ONLY, "member").status_code == 201
    resp = _put(client, project_id, NOTE_A, [U_MEMBER_ONLY], actor=U_MEMBER_ONLY)
    assert resp.status_code == 403, resp.text


def test_pn_nw_06_put_silently_ignores_pm_user_id(client):
    created = create_project(client, U_PM)
    project_id = created["id"]
    assert _add(client, project_id, U_MEMBER_ONLY, "member").status_code == 201
    resp = _put(client, project_id, NOTE_A, [U_PM, U_MEMBER_ONLY])
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_ids"] == [U_MEMBER_ONLY]
    assert U_PM not in _grants(client, project_id, NOTE_A)


def test_pn_nw_stale_grant_hidden_after_manual_orphan(client):
    """List intersects members — orphaned grant rows must not appear."""
    import uuid

    from app.db import session_scope
    from app.models.ge import GeProjectNoteWriteGrant
    from app.services.ge_graph import now_iso

    created = create_project(client, U_PM)
    project_id = created["id"]
    with session_scope() as db:
        now = now_iso()
        db.add(
            GeProjectNoteWriteGrant(
                id=str(uuid.uuid4()),
                project_id=project_id,
                note_id=NOTE_A,
                user_id=U_STRANGER,
                created_at=now,
                updated_at=now,
            )
        )
    assert U_STRANGER not in _grants(client, project_id, NOTE_A)
