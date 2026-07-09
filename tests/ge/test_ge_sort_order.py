"""GE-T162～T168 · M32 goal chain sibling sort_order."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers


def _create_dept(client, name: str = "研发部", manager: str = "u-owner") -> str:
    resp = client.post(
        "/api/v1/org/departments",
        headers=service_headers("reviewer-1"),
        json={"name": name, "manager_user_id": manager},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _annual_company(client, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1"),
        json={"planning_year": year},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_sub(client, company_id: str, name: str, dept_id: str) -> str:
    resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("reviewer-1"),
        json={
            "name": name,
            "parent_id": company_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_program(client, sub_id: str, name: str, dept_id: str) -> str:
    resp = client.post(
        "/api/v1/ge/programs",
        headers=service_headers("reviewer-1"),
        json={
            "name": name,
            "objective_id": sub_id,
            "owner_user_id": "u-owner",
            "primary_department_id": dept_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_project(client, program_id: str, name: str) -> str:
    resp = client.post(
        "/api/v1/ge/projects",
        headers=jwt_headers("u-owner"),
        json={
            "name": name,
            "pm_user_id": "u-owner",
            "program_id": program_id,
            "phases": [{"sequence": 1, "name": "阶段1", "gate_items": [], "tasks": []}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _find_company(client, company_id: str) -> dict:
    resp = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    return next(item for item in resp.json() if item["id"] == company_id)


def test_migration_sort_order_columns(client):
    """GE-T162: sort_order columns exist and new siblings get ascending orders."""
    dept_id = _create_dept(client)
    company = _annual_company(client, 2026)
    sub_a = _create_sub(client, company["id"], "Alpha", dept_id)
    sub_b = _create_sub(client, company["id"], "Beta", dept_id)

    listed = _find_company(client, company["id"])
    children = listed["children"]
    assert len(children) == 2
    assert all("sort_order" in child for child in children)
    orders = [child["sort_order"] for child in children]
    assert orders == sorted(orders)
    assert {child["id"] for child in children} == {sub_a, sub_b}


def test_sub_objective_reorder(client):
    """GE-T163: reorder sub-objectives under company."""
    dept_id = _create_dept(client)
    company = _annual_company(client, 2026)
    sub_a = _create_sub(client, company["id"], "Alpha", dept_id)
    sub_b = _create_sub(client, company["id"], "Beta", dept_id)

    resp = client.post(
        f"/api/v1/ge/objectives/{sub_a}/reorder",
        headers=service_headers("reviewer-1"),
        json={"direction": "down"},
    )
    assert resp.status_code == 200

    listed = _find_company(client, company["id"])
    child_ids = [child["id"] for child in listed["children"]]
    assert child_ids == [sub_b, sub_a]


def test_program_reorder(client):
    """GE-T164: reorder programs under sub-objective."""
    dept_id = _create_dept(client)
    company = _annual_company(client, 2026)
    sub_id = _create_sub(client, company["id"], "子线", dept_id)
    prog_a = _create_program(client, sub_id, "专项A", dept_id)
    prog_b = _create_program(client, sub_id, "专项B", dept_id)

    resp = client.post(
        f"/api/v1/ge/programs/{prog_b}/reorder",
        headers=service_headers("reviewer-1"),
        json={"direction": "up"},
    )
    assert resp.status_code == 200

    listed = _find_company(client, company["id"])
    sub = next(child for child in listed["children"] if child["id"] == sub_id)
    program_ids = [program["id"] for program in sub["programs"]]
    assert program_ids == [prog_b, prog_a]


def test_project_reorder(client):
    """GE-T165: reorder projects under program."""
    dept_id = _create_dept(client)
    company = _annual_company(client, 2026)
    sub_id = _create_sub(client, company["id"], "子线", dept_id)
    program_id = _create_program(client, sub_id, "专项", dept_id)
    proj_a = _create_project(client, program_id, "项目A")
    proj_b = _create_project(client, program_id, "项目B")

    resp = client.post(
        f"/api/v1/ge/projects/{proj_b}/reorder",
        headers=service_headers("reviewer-1"),
        json={"direction": "up"},
    )
    assert resp.status_code == 200

    detail = client.get(
        f"/api/v1/ge/programs/{program_id}",
        headers=jwt_headers("u-owner"),
    ).json()
    project_ids = [project["id"] for project in detail["projects"]]
    assert project_ids == [proj_b, proj_a]


def test_copy_year_preserves_sort_order(client):
    """GE-T166: copy_from_year preserves sub/program sort_order."""
    dept_id = _create_dept(client)
    source = _annual_company(client, 2026)
    sub_id = _create_sub(client, source["id"], "子线", dept_id)
    prog_first = _create_program(client, sub_id, "First", dept_id)
    prog_second = _create_program(client, sub_id, "Second", dept_id)
    client.post(
        f"/api/v1/ge/programs/{prog_second}/reorder",
        headers=service_headers("reviewer-1"),
        json={"direction": "up"},
    )

    target = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("reviewer-1"),
        json={"planning_year": 2027, "copy_from_year": 2026},
    ).json()

    listed = _find_company(client, target["id"])
    sub = listed["children"][0]
    assert sub["name"] == "子线"
    copied_program_ids = [program["id"] for program in sub["programs"]]
    assert copied_program_ids != [prog_first, prog_second]
    copied_orders = [program["sort_order"] for program in sub["programs"]]
    source_sub = next(child for child in _find_company(client, source["id"])["children"] if child["name"] == "子线")
    source_orders = sorted(program["sort_order"] for program in source_sub["programs"])
    assert copied_orders == source_orders


def test_annual_roots_sorted_by_year_desc(client):
    """GE-T167: annual company roots appear in planning_year descending order."""
    _annual_company(client, 2024)
    _annual_company(client, 2026)

    resp = client.get("/api/v1/ge/objectives", headers=jwt_headers("u-1"))
    assert resp.status_code == 200
    annual_roots = [
        item
        for item in resp.json()
        if item.get("level") == "company" and not item.get("is_default")
    ]
    years = [item.get("planning_year") for item in annual_roots if item.get("planning_year")]
    assert years == sorted(years, reverse=True)


def test_reorder_blocked_for_archived(client):
    """GE-T168: archived objectives cannot reorder."""
    from app.db import session_scope
    from app.models.ge import GeObjective

    dept_id = _create_dept(client)
    company = _annual_company(client, 2026)
    sub_id = _create_sub(client, company["id"], "归档子线", dept_id)
    with session_scope() as db:
        obj = db.get(GeObjective, sub_id)
        assert obj is not None
        obj.lifecycle_status = "archived"
        db.commit()
    resp_archived = client.post(
        f"/api/v1/ge/objectives/{sub_id}/reorder",
        headers=service_headers("reviewer-1"),
        json={"direction": "down"},
    )
    assert resp_archived.status_code == 403
    assert resp_archived.json()["detail"] == "strategic_locked"
