"""GE-T220～T227 · M41 项目管理 BP."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from app.db import get_session_factory
from app.models.ge import GeAuditEvent
from app.services import ge_goal_subtree_governor
from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import (
    GOLDEN_PROJECT_BODY,
    U_PM,
    U_STRANGER,
    create_project,
    get_graph,
)

U_OWNER_A = "931"
U_PMBP_B = "932"
U_OWNER_C = "933"
U_OWNER_D = "934"
REV = service_headers("800", is_reviewer=True)


def _detail(resp) -> str:
    body = resp.json()
    d = body.get("detail", body)
    if isinstance(d, dict):
        return str(d.get("detail") or "")
    return str(d)


def _annual(client, *, name: str, owner: str, year: int = 2026) -> dict:
    resp = client.post(
        "/api/v1/ge/objectives/years",
        headers=REV,
        json={"planning_year": year, "name": name, "owner_user_id": owner},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _sub_and_program(client, parent_id: str, *, owner: str, name: str = "M41子目标") -> tuple[dict, dict]:
    sub = client.post(
        "/api/v1/ge/objectives",
        headers=REV,
        json={
            "name": name,
            "parent_id": parent_id,
            "owner_user_id": owner,
            "primary_department_id": "test-dept-m41",
            "period_granularity": "year",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert sub.status_code == 201, sub.text
    prog = client.post(
        "/api/v1/ge/programs",
        headers=REV,
        json={
            "name": f"{name}-专项",
            "objective_id": sub.json()["id"],
            "owner_user_id": owner,
            "primary_department_id": "test-dept-m41",
        },
    )
    assert prog.status_code == 201, prog.text
    from app.db import get_session_factory
    from app.models.ge import GeProgram

    program_id = prog.json()["id"]
    with get_session_factory()() as db:
        program = db.get(GeProgram, program_id)
        assert program is not None
        program.period_start = "2026-01-01"
        program.period_end = "2026-12-31"
        program.period_granularity = "year"
        db.commit()
    return sub.json(), prog.json()


def _appoint_pmbp(client, *, kind: str, node_id: str, pmbp: str) -> dict:
    path = f"/api/v1/ge/objectives/{node_id}" if kind == "objective" else f"/api/v1/ge/programs/{node_id}"
    resp = client.patch(path, headers=REV, json={"pmbp_user_id": pmbp})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_ge_t220_pmbp_can_read_govern_stranger_403(client):
    """GE-T220: 仅 PMBP：子树 can_read/can_govern · stranger 403."""
    company = _annual(client, name="2026 M41 T220", owner=U_OWNER_A)
    _appoint_pmbp(client, kind="objective", node_id=company["id"], pmbp=U_PMBP_B)
    _sub, prog = _sub_and_program(client, company["id"], owner=U_OWNER_C)
    created = create_project(client, U_PMBP_B, {**GOLDEN_PROJECT_BODY, "program_id": prog["id"]})
    pid = created["id"]

    listed = client.get("/api/v1/ge/projects", headers=jwt_headers(U_PMBP_B))
    assert listed.status_code == 200
    assert pid in {p["id"] for p in listed.json()}

    graph = client.get(f"/api/v1/ge/projects/{pid}/graph", headers=jwt_headers(U_PMBP_B))
    assert graph.status_code == 200
    assert graph.json()["graph_editable"] is True

    patch = client.patch(
        f"/api/v1/ge/projects/{pid}",
        headers=jwt_headers(U_PMBP_B),
        json={"name": "pmbp-renamed"},
    )
    assert patch.status_code == 200, patch.text

    stranger = client.get(f"/api/v1/ge/projects/{pid}/graph", headers=jwt_headers(U_STRANGER))
    assert stranger.status_code == 403


def test_ge_t221_company_pmbp_sees_descendants_not_sibling_root(client):
    """GE-T221: 公司 PMBP 见下级；sibling 年组不可见."""
    company = _annual(client, name="2026 M41 T221-A", owner=U_OWNER_A)
    _appoint_pmbp(client, kind="objective", node_id=company["id"], pmbp=U_PMBP_B)
    _sub, prog = _sub_and_program(client, company["id"], owner=U_OWNER_C, name="T221可见")
    visible = create_project(client, U_PMBP_B, {**GOLDEN_PROJECT_BODY, "program_id": prog["id"]})

    sibling = _annual(client, name="2026 M41 T221-D", owner=U_OWNER_D)
    _sub_d, prog_d = _sub_and_program(client, sibling["id"], owner=U_OWNER_D, name="T221兄弟")
    hidden = create_project(client, U_OWNER_D, {**GOLDEN_PROJECT_BODY, "program_id": prog_d["id"]})

    listed = client.get("/api/v1/ge/projects", headers=jwt_headers(U_PMBP_B))
    ids = {p["id"] for p in listed.json()}
    assert visible["id"] in ids
    assert hidden["id"] not in ids

    hidden_graph = client.get(
        f"/api/v1/ge/projects/{hidden['id']}/graph", headers=jwt_headers(U_PMBP_B)
    )
    assert hidden_graph.status_code == 403


def test_ge_t222_pmbp_cannot_patch_owner(client):
    """GE-T222: PMBP PATCH owner_user_id → 403."""
    company = _annual(client, name="2026 M41 T222", owner=U_OWNER_A)
    _appoint_pmbp(client, kind="objective", node_id=company["id"], pmbp=U_PMBP_B)
    denied = client.patch(
        f"/api/v1/ge/objectives/{company['id']}",
        headers=jwt_headers(U_PMBP_B),
        json={"owner_user_id": U_PMBP_B},
    )
    assert denied.status_code == 403
    assert _detail(denied) == "not_goal_direct_owner"


def test_ge_t223_pmbp_cannot_activate_deviation(client, monkeypatch):
    """GE-T223: PMBP activate 偏差 → 403（仅 PM）."""
    monkeypatch.setattr("app.services.ge_deviations.dispatch_deviation_personal_assistant", lambda **k: None)
    company = _annual(client, name="2026 M41 T223", owner=U_OWNER_A)
    _appoint_pmbp(client, kind="objective", node_id=company["id"], pmbp=U_PMBP_B)
    _sub, prog = _sub_and_program(client, company["id"], owner=U_OWNER_C)
    created = create_project(client, U_PMBP_B, {**GOLDEN_PROJECT_BODY, "program_id": prog["id"]})
    graph = get_graph(client, created["id"], U_PM)
    gi = next(
        gi for phase in graph["phases"] for gi in phase["gate_items"] if gi["name"] == "诊断报告"
    )
    with patch("app.services.ge_deviations.today_shanghai", return_value=date(2026, 6, 20)):
        opened = client.post(
            f"/api/v1/ge/gate-items/{gi['id']}/deviations/open",
            headers=jwt_headers(U_PM),
            json={"kind": "overdue"},
        )
    assert opened.status_code == 200, opened.text
    dev_id = opened.json()["deviation"]["id"]
    denied = client.patch(
        f"/api/v1/ge/deviations/{dev_id}",
        headers=jwt_headers(U_PMBP_B),
        json={"action": "activate", "remediation_due": "2026-06-10"},
    )
    assert denied.status_code == 403
    assert _detail(denied) == "not_project_pm"


def test_ge_t224_list_projects_no_per_row_governor(client, monkeypatch):
    """GE-T224: list_projects 仍无 per-project governor 调用（GE-PERF-04 回归）."""
    company = _annual(client, name="2026 M41 T224", owner=U_OWNER_A)
    _appoint_pmbp(client, kind="objective", node_id=company["id"], pmbp=U_PMBP_B)
    _sub, prog = _sub_and_program(client, company["id"], owner=U_OWNER_C)
    create_project(client, U_PMBP_B, {**GOLDEN_PROJECT_BODY, "program_id": prog["id"]})

    calls: list[str] = []

    def _spy(**kwargs):
        calls.append(str(kwargs.get("project_id") or kwargs.get("program_id")))
        raise AssertionError("is_goal_subtree_governor must not run in list_projects filter loop")

    monkeypatch.setattr(ge_goal_subtree_governor, "is_goal_subtree_governor", _spy)
    monkeypatch.setattr("app.services.ge_access.is_goal_subtree_governor", _spy)

    resp = client.get("/api/v1/ge/projects", headers=jwt_headers(U_PMBP_B))
    assert resp.status_code == 200, resp.text
    assert calls == []
    assert len(resp.json()) >= 1


def test_ge_t225_portfolio_accountable_excludes_pmbp_only(client):
    """GE-T225: portfolio accountable 不含 PMBP-only 行."""
    company = _annual(client, name="2026 M41 T225", owner=U_OWNER_A)
    _appoint_pmbp(client, kind="objective", node_id=company["id"], pmbp=U_PMBP_B)
    portfolio = client.get(
        f"/api/v1/ge/portfolios/users/{U_PMBP_B}",
        headers=REV,
    )
    assert portfolio.status_code == 200, portfolio.text
    rows = portfolio.json().get("accountable") or []
    assert not any(row.get("user_id") == U_PMBP_B for row in rows)
    owner_port = client.get(f"/api/v1/ge/portfolios/users/{U_OWNER_A}", headers=REV)
    assert owner_port.status_code == 200
    assert any(row.get("user_id") == U_OWNER_A for row in owner_port.json().get("accountable") or [])


def test_ge_t226_owner_appoints_pmbp_then_pmbp_cannot_rewrite(client):
    """GE-T226: owner 任命 BP → 200 + audit；PMBP 再 PATCH pmbp → 403."""
    company = _annual(client, name="2026 M41 T226", owner=U_OWNER_A)
    ok = client.patch(
        f"/api/v1/ge/objectives/{company['id']}",
        headers=jwt_headers(U_OWNER_A),
        json={"pmbp_user_id": U_PMBP_B},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["pmbp_user_id"] == U_PMBP_B

    with get_session_factory()() as db:
        events = (
            db.query(GeAuditEvent)
            .filter(GeAuditEvent.action == "patch_pmbp", GeAuditEvent.entity_id == company["id"])
            .all()
        )
        assert events
        assert events[-1].actor_user_id == U_OWNER_A

    denied = client.patch(
        f"/api/v1/ge/objectives/{company['id']}",
        headers=jwt_headers(U_PMBP_B),
        json={"pmbp_user_id": U_OWNER_C},
    )
    assert denied.status_code == 403
    assert _detail(denied) == "not_pmbp_appointer"


def test_ge_t227_effective_pmbp_inherited_from_parent(client):
    """GE-T227: 子节点 pmbp 空、父有 BP → effective_pmbp_user_id + inherited_from."""
    company = _annual(client, name="2026 M41 T227", owner=U_OWNER_A)
    _appoint_pmbp(client, kind="objective", node_id=company["id"], pmbp=U_PMBP_B)
    sub, prog = _sub_and_program(client, company["id"], owner=U_OWNER_C, name="T227子")
    assert sub.get("pmbp_user_id") in (None, "")
    assert sub["effective_pmbp_user_id"] == U_PMBP_B
    inherited = sub.get("effective_pmbp_inherited_from") or {}
    assert inherited.get("id") == company["id"]
    assert inherited.get("kind") == "objective"
    assert prog["effective_pmbp_user_id"] == U_PMBP_B
    assert (prog.get("effective_pmbp_inherited_from") or {}).get("id") == company["id"]
