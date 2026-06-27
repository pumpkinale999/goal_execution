"""Nested department tests."""

from __future__ import annotations

from tests.conftest import service_headers


def _create_dept(client, name: str, *, parent_id: str | None = None) -> str:
    body: dict[str, str] = {"name": name}
    if parent_id is not None:
        body["parent_id"] = parent_id
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json=body,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == name
    assert data.get("parent_id") == parent_id
    return data["id"]


def test_create_nested_departments(client):
    root_id = _create_dept(client, "集团总部")
    child_id = _create_dept(client, "研发中心", parent_id=root_id)
    grand_id = _create_dept(client, "平台部", parent_id=child_id)

    listed = client.get("/api/v1/org/departments", headers=service_headers("reviewer-1")).json()
    by_id = {d["id"]: d for d in listed}
    assert by_id[child_id]["parent_id"] == root_id
    assert by_id[grand_id]["parent_id"] == child_id
    assert by_id[root_id].get("parent_id") in (None, "")


def test_delete_department_blocked_when_children_exist(client):
    root_id = _create_dept(client, "事业部")
    _create_dept(client, "子部门", parent_id=root_id)

    resp = client.delete(
        f"/api/v1/org/departments/{root_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    if isinstance(detail, dict):
        assert detail.get("detail") == "department_has_children"
    else:
        assert "department_has_children" in str(detail)


def test_delete_department_when_no_children_or_teams(client):
    root_id = _create_dept(client, "可删部门")
    resp = client.delete(
        f"/api/v1/org/departments/{root_id}",
        headers=service_headers("reviewer-1"),
    )
    assert resp.status_code == 204


def test_patch_department_reparent(client):
    root_id = _create_dept(client, "集团总部")
    child_id = _create_dept(client, "研发中心", parent_id=root_id)
    sibling_id = _create_dept(client, "销售中心", parent_id=root_id)

    resp = client.patch(
        f"/api/v1/org/departments/{child_id}",
        headers=service_headers("reviewer-1"),
        json={"parent_id": sibling_id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["parent_id"] == sibling_id

    resp = client.patch(
        f"/api/v1/org/departments/{child_id}",
        headers=service_headers("reviewer-1"),
        json={"parent_id": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("parent_id") in (None, "")


def test_patch_department_reparent_cycle_blocked(client):
    root_id = _create_dept(client, "事业部")
    child_id = _create_dept(client, "子部门", parent_id=root_id)
    grand_id = _create_dept(client, "孙部门", parent_id=child_id)

    resp = client.patch(
        f"/api/v1/org/departments/{root_id}",
        headers=service_headers("reviewer-1"),
        json={"parent_id": grand_id},
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    if isinstance(detail, dict):
        assert detail.get("detail") == "department_cycle"
    else:
        assert "department_cycle" in str(detail)
