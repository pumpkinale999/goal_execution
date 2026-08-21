"""GE-T191～T196 · GE-T199 · M38 multi annual company roots."""

from __future__ import annotations

from tests.conftest import jwt_headers, service_headers


def _create_dept(client, name: str = "研发部", manager: str = "910") -> str:
    """Opaque dept id — GE org HTTP unmounted; authority lives in skstudio."""
    _ = (client, manager)
    return f"test-dept-{name}"


def _create_year(client, year: int, name: str, **extra) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": year, "name": name, **extra},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_second_active_root_same_year_owner_is_actor(client):
    """GE-T191: second active company root in same year; owner=actor."""
    first = _create_year(client, 2040, "A")
    assert first["name"] == "A"
    second = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2040, "name": "B"},
    )
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["name"] == "B"
    assert body["owner_user_id"] == "800"
    assert body["planning_year"] == 2040


def test_annual_root_limit_exceeded(client):
    """GE-T192: 10 formal company roots (incl archived) → next create 400."""
    from app.db import session_scope
    from app.models.ge import GeObjective

    roots = [_create_year(client, 2041, f"根{i}") for i in range(10)]
    with session_scope() as db:
        obj = db.get(GeObjective, roots[0]["id"])
        assert obj is not None
        obj.lifecycle_status = "archived"
        db.commit()

    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2041, "name": "第11根"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "annual_root_limit_exceeded"


def test_create_year_name_required(client):
    """GE-T193: missing or blank name → name_required."""
    missing = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2042},
    )
    assert missing.status_code == 400
    assert missing.json()["detail"] == "name_required"

    blank = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2042, "name": "  "},
    )
    assert blank.status_code == 400
    assert blank.json()["detail"] == "name_required"


def test_duplicate_annual_name_including_archived_and_patch(client):
    """GE-T194: duplicate name vs archived; PATCH rename uniqueness."""
    from app.db import session_scope
    from app.models.ge import GeObjective

    archived = _create_year(client, 2043, "A")
    with session_scope() as db:
        obj = db.get(GeObjective, archived["id"])
        assert obj is not None
        obj.lifecycle_status = "archived"
        db.commit()

    other = _create_year(client, 2043, "B")
    dup_create = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2043, "name": "A"},
    )
    assert dup_create.status_code == 400
    assert dup_create.json()["detail"] == "duplicate_annual_name"

    dup_patch = client.patch(
        f"/api/v1/ge/objectives/{other['id']}",
        headers=service_headers("800", is_reviewer=True),
        json={"name": "A"},
    )
    assert dup_patch.status_code == 400
    assert dup_patch.json()["detail"] == "duplicate_annual_name"


def test_copy_from_objective_id_across_years(client):
    """GE-T195: copy subtree from specific source root across years."""
    dept_id = _create_dept(client)
    source = _create_year(client, 2026, "源根S")
    sibling = _create_year(client, 2026, "同年另一根")
    sub_s = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": "S子目标",
            "parent_id": source["id"],
            "owner_user_id": "910",
            "primary_department_id": dept_id,
        },
    )
    assert sub_s.status_code == 201, sub_s.text
    sub_other = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": "不应被复制",
            "parent_id": sibling["id"],
            "owner_user_id": "910",
            "primary_department_id": dept_id,
        },
    )
    assert sub_other.status_code == 201, sub_other.text

    target = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={
            "planning_year": 2027,
            "name": "2027 新根",
            "copy_from_objective_id": source["id"],
        },
    )
    assert target.status_code == 201, target.text
    tree = client.get("/api/v1/ge/objectives", headers=jwt_headers("801")).json()
    new_root = next(item for item in tree if item["id"] == target.json()["id"])
    child_names = [child["name"] for child in new_root.get("children", [])]
    assert child_names == ["S子目标"]
    assert "不应被复制" not in child_names


def test_copy_from_year_deprecated(client):
    """GE-T196: copy_from_year → 400 copy_from_year_deprecated."""
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={"planning_year": 2046, "name": "仍带旧字段", "copy_from_year": 2045},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "copy_from_year_deprecated"


def test_copy_source_invalid(client):
    """GE-T199: copy from sub id or missing id → copy_source_invalid."""
    dept_id = _create_dept(client)
    company = _create_year(client, 2026, "主根")
    sub_resp = client.post(
        "/api/v1/ge/objectives",
        headers=service_headers("800", is_reviewer=True),
        json={
            "name": "子目标",
            "parent_id": company["id"],
            "owner_user_id": "910",
            "primary_department_id": dept_id,
        },
    )
    assert sub_resp.status_code == 201, sub_resp.text
    sub = sub_resp.json()

    from_sub = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={
            "planning_year": 2027,
            "name": "非法复制子",
            "copy_from_objective_id": sub["id"],
        },
    )
    assert from_sub.status_code == 400
    assert from_sub.json()["detail"] == "copy_source_invalid"

    missing = client.post(
        "/api/v1/ge/objectives/years",
        headers=service_headers("800", is_reviewer=True),
        json={
            "planning_year": 2027,
            "name": "非法复制不存在",
            "copy_from_objective_id": "missing-objective-id",
        },
    )
    assert missing.status_code == 400
    assert missing.json()["detail"] == "copy_source_invalid"
