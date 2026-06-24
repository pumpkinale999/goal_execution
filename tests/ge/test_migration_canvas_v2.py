"""Migration 007 smoke."""

from __future__ import annotations

from tests.ge.conftest import U_PM, create_project, get_graph


def test_project_has_start_and_end_phases(client):
    created = create_project(client, U_PM)
    graph = get_graph(client, created["id"], U_PM)
    names = [p["name"] for p in graph["phases"]]
    assert names[0] == "开始"
    assert names[-1] == "结束"
    assert not any(e["kind"] == "gate_includes" for e in graph["edges"])
