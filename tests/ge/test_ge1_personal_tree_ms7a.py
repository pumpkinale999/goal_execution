"""GE1-T15 · DESK-GE1 MS7a subject personal-tree spine API."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_PM,
    U_STRANGER,
    create_project,
    ensure_formal_test_program,
)


U_OWNER = "910"


def _walk_objective_ids(nodes: list[dict]) -> set[str]:
    ids: set[str] = set()
    for node in nodes:
        ids.add(node["id"])
        ids |= _walk_objective_ids(node.get("children") or [])
    return ids


def _walk_program_ids(nodes: list[dict]) -> set[str]:
    ids: set[str] = set()
    for node in nodes:
        for p in node.get("programs") or []:
            ids.add(p["id"])
        ids |= _walk_program_ids(node.get("children") or [])
    return ids


def test_ge1_t15_subject_personal_tree_matches_actor_left_tree(client):
    """Subject path personal-tree ≡ same user as actor on GET /objectives."""
    program_id = ensure_formal_test_program(client, owner_user_id=U_OWNER)
    create_project(
        client,
        U_OWNER,
        {**GOLDEN_PROJECT_BODY, "program_id": program_id, "pm_user_id": U_PM},
    )

    actor_tree = client.get("/api/v1/ge/objectives", headers=jwt_headers(U_OWNER)).json()
    actor_obj = _walk_objective_ids(actor_tree)
    actor_prog = _walk_program_ids(actor_tree)

    # Reviewer service actor must still get *subject* non-reviewer geometry.
    spine = client.get(
        f"/api/v1/ge/portfolios/users/{U_OWNER}/personal-tree",
        headers=service_headers("800", is_reviewer=True),
    )
    assert spine.status_code == 200, spine.text
    body = spine.json()
    assert body["subject_user_id"] == U_OWNER
    spine_obj = {o["id"] for o in body["objectives"]}
    spine_prog = {p["id"] for p in body["programs"]}
    assert spine_obj == actor_obj
    assert program_id in spine_prog
    assert spine_prog == actor_prog

    # Hang fields present for BFF nest rebuild.
    by_id = {o["id"]: o for o in body["objectives"]}
    for oid in spine_obj:
        row = by_id[oid]
        assert "name" in row and "level" in row
    prog = next(p for p in body["programs"] if p["id"] == program_id)
    assert prog.get("objective_id")


def test_ge1_t15_stranger_empty_and_reviewer_actor_does_not_inflate(client):
    create_project(client, U_PM)
    empty = client.get(
        f"/api/v1/ge/portfolios/users/{U_STRANGER}/personal-tree",
        headers=service_headers("800", is_reviewer=True),
    )
    assert empty.status_code == 200, empty.text
    body = empty.json()
    assert body["objectives"] == []
    assert body["programs"] == []

    # Self service actor (non-reviewer) may read own spine.
    self_spine = client.get(
        f"/api/v1/ge/portfolios/users/{U_STRANGER}/personal-tree",
        headers=service_headers(U_STRANGER, is_reviewer=False),
    )
    assert self_spine.status_code == 200, self_spine.text
    assert self_spine.json()["programs"] == []
