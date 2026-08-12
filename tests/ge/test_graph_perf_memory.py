"""GE-PERF-GRAPH: selectin load + in-memory link maps; sense view skips effective_status."""

from __future__ import annotations

from sqlalchemy import event, inspect

from app.db import get_session_factory
from app.services.ge_graph import build_project_graph, load_project_graph
from tests.conftest import jwt_headers
from tests.ge.conftest import U_PM, create_project, get_graph


def test_graph_perf_indexes_exist(client):
    """029 migration / ORM Index: project graph FK lookup indexes present."""
    _ = client
    from app.db import get_engine

    insp = inspect(get_engine())
    task_idx = {i["name"] for i in insp.get_indexes("ge_tasks")}
    gi_idx = {i["name"] for i in insp.get_indexes("ge_gate_items")}
    dev_idx = {i["name"] for i in insp.get_indexes("ge_deviations")}
    assert "ix_ge_tasks_project_id" in task_idx
    assert "ix_ge_gate_items_phase_id" in gi_idx
    assert "ix_ge_deviations_project_status" in dev_idx


def _count_statements(session_bind, fn):
    statements: list[str] = []

    def before_cursor(conn, cursor, statement, parameters, context, executemany):
        statements.append(" ".join(str(statement).split())[:200])

    event.listen(session_bind, "before_cursor_execute", before_cursor)
    try:
        fn()
    finally:
        event.remove(session_bind, "before_cursor_execute", before_cursor)
    return statements


def test_load_project_graph_selectin_bounded_queries(client):
    created = create_project(client, U_PM)
    pid = created["id"]
    Session = get_session_factory()
    db = Session()
    try:
        stmts = _count_statements(db.get_bind(), lambda: load_project_graph(db, pid))
        # selectin: project + program + objective + phases + gates + gate_items + tasks
        assert 1 <= len(stmts) <= 12
        # Must not be a single mega JOIN of phases×items×tasks (historically 1 stmt ~1s).
        joined_collections = sum(
            1
            for s in stmts
            if "JOIN" in s.upper()
            and "ge_phases" in s.lower()
            and "ge_tasks" in s.lower()
            and "ge_gate_items" in s.lower()
        )
        assert joined_collections == 0
    finally:
        db.close()


def test_build_project_graph_no_actor_few_extra_queries(client):
    created = create_project(client, U_PM)
    pid = created["id"]
    Session = get_session_factory()
    db = Session()
    try:
        project = load_project_graph(db, pid)
        assert project is not None
        n_tasks = len(project.tasks)
        n_gi = sum(len(p.gate_items) for p in project.phases)
        old_link_lower_bound = n_tasks * 2 + n_gi  # produce+prereq per task + signers per gi
        stmts = _count_statements(
            db.get_bind(),
            lambda: build_project_graph(db, project, actor_user_id=None),
        )
        # Prefetch produce/prereq/include + one deviations query (no per-GI lookup).
        assert len(stmts) < old_link_lower_bound
        assert len(stmts) <= 5
        assert sum(1 for s in stmts if "ge_deviations" in s.lower()) <= 1
    finally:
        db.close()


def test_graph_sense_view_skips_effective_status(client):
    created = create_project(client, U_PM)
    pid = created["id"]
    canvas = get_graph(client, pid, U_PM)
    sense = client.get(
        f"/api/v1/ge/projects/{pid}/graph",
        headers=jwt_headers(U_PM),
        params={"view": "sense"},
    )
    assert sense.status_code == 200
    sense_g = sense.json()
    assert "definition_gaps" in sense_g
    canvas_has_eff = any(
        "effective_status" in t for p in canvas["phases"] for t in p.get("tasks") or []
    )
    sense_has_eff = any(
        "effective_status" in t for p in sense_g["phases"] for t in p.get("tasks") or []
    )
    assert canvas_has_eff
    assert not sense_has_eff
    assert "graph_editable" not in sense_g


def test_definition_gaps_matches_sense_graph_embed(client):
    created = create_project(client, U_PM)
    pid = created["id"]
    sense = client.get(
        f"/api/v1/ge/projects/{pid}/graph",
        headers=jwt_headers(U_PM),
        params={"view": "sense"},
    ).json()
    gaps_resp = client.get(
        f"/api/v1/ge/projects/{pid}/definition-gaps",
        headers=jwt_headers(U_PM),
    )
    assert gaps_resp.status_code == 200
    body = gaps_resp.json()
    embed_keys = {g.get("concern_key") for g in (sense.get("definition_gaps") or [])}
    api_keys = {g.get("concern_key") for g in (body.get("gaps") or [])}
    assert embed_keys == api_keys
    assert body.get("gap_count") == len(body.get("gaps") or [])
