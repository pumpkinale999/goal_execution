"""PRA M4: observation mount outbox + subscription."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.conftest import jwt_headers, service_headers
from tests.ge.conftest import U_PM, create_project, get_graph, phase_by_name


def _outbox_kinds(project_id: str) -> list[str]:
    from app.db import get_session_factory
    from app.models.observation_mount import GeObservationOutbox

    db = get_session_factory()()
    try:
        kinds = []
        for row in db.query(GeObservationOutbox).order_by(GeObservationOutbox.created_at.desc()).all():
            payload = row.payload or {}
            if payload.get("project_id") == project_id:
                kinds.append(str(payload.get("change_kind") or ""))
        return kinds
    finally:
        db.close()


def test_reject_unsupported_mount(client):
    r = client.post(
        "/api/v1/ge/observation/subscriptions",
        headers=service_headers("svc"),
        json={
            "name": "pra",
            "target_url": "http://127.0.0.1:8095/api/v1/active-agent/observations",
            "mount_point": "read_tip",
        },
    )
    assert r.status_code == 400


def test_reject_short_service_token(client):
    """CODE-005 M2: after_project_graph_write rejects tok_len < 16."""
    r = client.post(
        "/api/v1/ge/observation/subscriptions",
        headers=service_headers("svc"),
        json={
            "name": "pra-short",
            "target_url": "http://127.0.0.1:8095/api/v1/active-agent/observations",
            "service_token": "test-short",
            "mount_point": "after_project_graph_write",
        },
    )
    assert r.status_code == 400
    assert "service_token_too_short" in str(r.json())


def test_register_and_enqueue_outbox(client, ge_db):
    from app.db import get_session_factory
    from app.services.observation_mount import enqueue_after_project_graph_write, register_subscription

    r = client.post(
        "/api/v1/ge/observation/subscriptions",
        headers=service_headers("svc"),
        json={
            "name": "pra",
            "target_url": "http://127.0.0.1:8095/api/v1/active-agent/observations",
            "service_token": "aa-service-tok16",
            "mount_point": "after_project_graph_write",
        },
    )
    assert r.status_code == 200
    assert r.json()["name"] == "pra"

    db = get_session_factory()()
    try:
        with patch(
            "app.services.observation_mount.load_project_graph",
            return_value=None,
        ):
            rows = enqueue_after_project_graph_write(
                db,
                project_id="p-missing",
                change_kind="gate_item_patch",
                include_graph=False,
            )
            db.commit()
        assert len(rows) == 1
        assert rows[0].status == "pending"
        assert rows[0].payload["project_id"] == "p-missing"
    finally:
        db.close()

    listed = client.get(
        "/api/v1/ge/observation/outbox",
        headers=service_headers("svc"),
        params={"status_filter": "pending"},
    )
    assert listed.status_code == 200
    assert len(listed.json()["items"]) >= 1


def test_deliver_retry_and_success(client):
    from app.db import get_session_factory
    from app.services.observation_mount import (
        deliver_pending,
        enqueue_after_project_graph_write,
        register_subscription,
    )

    db = get_session_factory()()
    try:
        register_subscription(
            db,
            name="pra-deliver",
            target_url="http://example.test/obs",
            service_token="aa-service-tok16",
        )
        enqueue_after_project_graph_write(
            db, project_id="p1", change_kind="test", include_graph=False
        )
        db.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.post", return_value=mock_resp):
            deliver_pending(db)
            db.commit()

        mock_ok = MagicMock()
        mock_ok.status_code = 200
        with patch("httpx.post", return_value=mock_ok):
            result = deliver_pending(db)
            db.commit()
        assert result["delivered"] >= 1
    finally:
        db.close()

    listed = client.get(
        "/api/v1/ge/observation/outbox",
        headers=service_headers("svc"),
    )
    assert any(i["status"] == "delivered" for i in listed.json()["items"])


def test_patch_phase_and_add_task_enqueue(client):
    with patch("app.services.observation_mount.schedule_flush_soon"):
        created = create_project(client, U_PM)
        project_id = created["id"]
        graph = get_graph(client, project_id, U_PM)
        dev = phase_by_name(graph, "开发")

        patched = client.patch(
            f"/api/v1/ge/phases/{dev['id']}",
            headers=jwt_headers(U_PM),
            json={"name": "开发-obs", "planned_start": "2026-06-16", "planned_end": "2026-06-30"},
        )
        assert patched.status_code == 200, patched.text

        added = client.post(
            f"/api/v1/ge/projects/{project_id}/phases/{dev['id']}/tasks",
            headers=jwt_headers(U_PM),
            json={"title": "观测入队任务", "assignee_user_id": U_PM},
        )
        assert added.status_code == 200, added.text

    kinds = _outbox_kinds(project_id)
    assert "phase_patch" in kinds
    assert "task_add" in kinds
    assert "project_create" in kinds


def test_outbox_graph_is_sense_lite_with_definition_gaps(client):
    """Write-mount payload matches GET …/graph?view=sense (no effective_status)."""
    from app.db import get_session_factory
    from app.models.observation_mount import GeObservationOutbox
    from app.services.observation_mount import enqueue_after_project_graph_write

    created = create_project(client, U_PM)
    project_id = created["id"]
    db = get_session_factory()()
    try:
        rows = enqueue_after_project_graph_write(
            db,
            project_id=project_id,
            change_kind="test_sense_lite",
            include_graph=True,
        )
        db.commit()
        assert len(rows) == 1
        graph = (rows[0].payload or {}).get("project_graph") or {}
        assert "definition_gaps" in graph
        assert isinstance(graph["definition_gaps"], list)
        for phase in graph.get("phases") or []:
            for task in phase.get("tasks") or []:
                assert "effective_status" not in task
        stored = (
            db.query(GeObservationOutbox)
            .filter(GeObservationOutbox.id == rows[0].id)
            .one()
        )
        assert stored.payload["change_kind"] == "test_sense_lite"
    finally:
        db.close()


def test_produce_link_and_patch_task_enqueue(client):
    with patch("app.services.observation_mount.schedule_flush_soon"):
        created = create_project(client, U_PM)
        project_id = created["id"]
        graph = get_graph(client, project_id, U_PM)
        plan = phase_by_name(graph, "方案")
        task_id = plan["tasks"][0]["id"]
        gate_item_id = plan["gate_items"][0]["id"]

        produce = client.post(
            f"/api/v1/ge/tasks/{task_id}/produces",
            headers=jwt_headers(U_PM),
            json={"gate_item_id": gate_item_id},
        )
        assert produce.status_code == 200, produce.text

        patched = client.patch(
            f"/api/v1/ge/tasks/{task_id}",
            headers=jwt_headers(U_PM),
            json={"title": "观测补丁任务"},
        )
        assert patched.status_code == 200, patched.text

    kinds = _outbox_kinds(project_id)
    assert "produce_link_add" in kinds
    assert "task_patch" in kinds


def test_graph_write_flush_delivers_to_subscriber(client):
    from app.db import get_session_factory
    from app.models.observation_mount import GeObservationOutbox
    from app.services.observation_mount import deliver_pending

    mock_ok = MagicMock()
    mock_ok.status_code = 200
    with (
        patch("app.services.observation_mount.schedule_flush_soon"),
        patch("httpx.post", return_value=mock_ok) as post,
    ):
        created = create_project(client, U_PM)
        project_id = created["id"]
        reg = client.post(
            "/api/v1/ge/observation/subscriptions",
            headers=service_headers("svc"),
            json={
                "name": "pra-write-flush",
                "target_url": "http://aa.test/api/v1/active-agent/observations",
                "service_token": "aa-service-tok16",
                "mount_point": "after_project_graph_write",
            },
        )
        assert reg.status_code == 200

        graph = get_graph(client, project_id, U_PM)
        dev = phase_by_name(graph, "开发")
        patched = client.patch(
            f"/api/v1/ge/phases/{dev['id']}",
            headers=jwt_headers(U_PM),
            json={"name": "开发-flush", "planned_start": "2026-06-16", "planned_end": "2026-06-30"},
        )
        assert patched.status_code == 200, patched.text

        db = get_session_factory()()
        try:
            result = deliver_pending(db)
            db.commit()
            delivered_phase = (
                db.query(GeObservationOutbox)
                .filter(GeObservationOutbox.status == "delivered")
                .all()
            )
            assert any(
                (r.payload or {}).get("project_id") == project_id
                and (r.payload or {}).get("change_kind") == "phase_patch"
                for r in delivered_phase
            )
        finally:
            db.close()

        assert result["delivered"] >= 1
        assert post.called
        assert any(
            str(c.args[0]).endswith("/api/v1/active-agent/observations")
            for c in post.call_args_list
        )


def test_requeue_dead_outbox_by_401_error(client):
    """CODE-005 M4: dead + last_error containing 401 → pending; unrelated dead untouched."""
    from app.db import get_session_factory
    from app.models.observation_mount import GeObservationOutbox

    db = get_session_factory()()
    try:
        dead_401 = GeObservationOutbox(
            id="obs-dead-401",
            idempotency_key="ge:after_project_graph_write:p1:dead401",
            mount_point="after_project_graph_write",
            payload={"project_id": "p1", "change_kind": "probe"},
            status="dead",
            attempts=5,
            last_error="pra:401",
            created_at="2026-08-10T00:00:00Z",
        )
        dead_other = GeObservationOutbox(
            id="obs-dead-500",
            idempotency_key="ge:after_project_graph_write:p1:dead500",
            mount_point="after_project_graph_write",
            payload={"project_id": "p1", "change_kind": "probe"},
            status="dead",
            attempts=5,
            last_error="pra:500",
            created_at="2026-08-10T00:00:01Z",
        )
        db.add(dead_401)
        db.add(dead_other)
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/api/v1/ge/observation/outbox/requeue",
        headers=service_headers("svc"),
        json={"error_substr": "401"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["requeued"] >= 1
    assert "obs-dead-401" in body["ids"]
    assert "obs-dead-500" not in body["ids"]

    db = get_session_factory()()
    try:
        a = db.query(GeObservationOutbox).filter(GeObservationOutbox.id == "obs-dead-401").one()
        b = db.query(GeObservationOutbox).filter(GeObservationOutbox.id == "obs-dead-500").one()
        assert a.status == "pending"
        assert a.attempts == 0
        assert a.last_error is None
        assert b.status == "dead"
        assert b.attempts == 5
    finally:
        db.close()


def test_deliver_pending_marks_failure_when_subscriber_returns_401():
    """Wrong AA service_token → observations 401 → outbox stays pending / dead (CODE-004)."""
    from app.db import get_session_factory
    from app.models.observation_mount import GeObservationOutbox
    from app.services.observation_mount import deliver_pending, register_subscription

    db = get_session_factory()()
    try:
        register_subscription(
            db,
            name="pra-bad-token",
            target_url="http://aa.test/api/v1/active-agent/observations",
            service_token="wrong-token-16ch",
            mount_point="after_project_graph_write",
        )
        row = GeObservationOutbox(
            id="obs-401-test",
            idempotency_key="ge:after_project_graph_write:p1:401test",
            mount_point="after_project_graph_write",
            payload={
                "idempotency_key": "ge:after_project_graph_write:p1:401test",
                "project_id": "p1",
                "change_kind": "probe",
            },
            status="pending",
            attempts=0,
            created_at="2026-08-10T00:00:00Z",
        )
        db.add(row)
        db.commit()

        mock_401 = MagicMock()
        mock_401.status_code = 401
        with patch("httpx.post", return_value=mock_401) as post:
            result = deliver_pending(db)
            db.commit()
            assert post.called
            assert result["delivered"] == 0
            refreshed = db.query(GeObservationOutbox).filter(GeObservationOutbox.id == "obs-401-test").one()
            assert refreshed.status == "pending"
            assert refreshed.attempts == 1
            assert refreshed.last_error and "401" in refreshed.last_error
    finally:
        db.rollback()
        db.close()
