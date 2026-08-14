"""Observation mount enqueue + deliver (after_project_graph_write)."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.observation_mount import GeObservationOutbox, GeObservationSubscription
from app.services.ge_graph import load_project_graph, now_iso

logger = logging.getLogger(__name__)

MOUNT_AFTER_GRAPH_WRITE = "after_project_graph_write"
MAX_ATTEMPTS = 5
FLUSH_INTERVAL_SEC = 45.0
# CODE-005 M2: reject short tokens that caused observations 401 (e.g. "test…").
MIN_SERVICE_TOKEN_LEN = 16

_flush_lock = threading.Lock()
_flush_stop = threading.Event()
_flush_thread: threading.Thread | None = None


def _payload_as_dict(payload: Any) -> dict[str, Any]:
    """Coerce outbox payload to a dict for HTTP JSON body.

    Postgres/psycopg may surface SQLAlchemy ``JSON`` columns as ``str``; posting that
    via ``httpx.post(..., json=payload)`` double-encodes a JSON string and AA returns
    422 (``Input should be a valid dictionary``).
    """
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise TypeError(f"outbox_payload_not_object:{type(data).__name__}")
        return data
    raise TypeError(f"outbox_payload_unsupported:{type(payload).__name__}")


def register_subscription(
    db: Session,
    *,
    name: str,
    target_url: str,
    service_token: str = "",
    mount_point: str = MOUNT_AFTER_GRAPH_WRITE,
) -> GeObservationSubscription:
    if not name.strip() or not target_url.strip():
        raise ValueError("invalid_subscription")
    if mount_point != MOUNT_AFTER_GRAPH_WRITE and mount_point != "project_lifecycle":
        raise ValueError("unsupported_mount_point")
    token = (service_token or "").strip()
    if mount_point == MOUNT_AFTER_GRAPH_WRITE and len(token) < MIN_SERVICE_TOKEN_LEN:
        raise ValueError("service_token_too_short")
    existing = db.query(GeObservationSubscription).filter(GeObservationSubscription.name == name).first()
    if existing:
        existing.target_url = target_url
        existing.service_token = token
        existing.mount_point = mount_point
        existing.enabled = True
        db.add(existing)
        db.flush()
        return existing
    row = GeObservationSubscription(
        id=uuid.uuid4().hex,
        name=name.strip(),
        mount_point=mount_point,
        target_url=target_url.strip(),
        service_token=token,
        enabled=True,
        created_at=now_iso(),
    )
    db.add(row)
    db.flush()
    return row


def enqueue_after_project_graph_write(
    db: Session,
    *,
    project_id: str,
    change_kind: str,
    entity_refs: dict[str, Any] | None = None,
    include_graph: bool = True,
) -> list[GeObservationOutbox]:
    """Insert outbox row after a successful graph write (same session / before commit)."""
    graph = None
    if include_graph:
        loaded = load_project_graph(db, project_id)
        if loaded is not None:
            from app.services.ge_assess_definition import attach_definition_gaps
            from app.services.ge_graph import build_project_graph

            try:
                # Sense-lite: no Canvas effective_status (same as GET …/graph?view=sense).
                graph = attach_definition_gaps(
                    build_project_graph(db, loaded, actor_user_id=None, is_governor=False)
                )
            except Exception:
                logger.exception("observation_graph_build_failed")
                graph = None

    key = f"ge:{MOUNT_AFTER_GRAPH_WRITE}:{project_id}:{uuid.uuid4().hex[:12]}"
    payload = {
        "idempotency_key": key,
        "occurred_at": now_iso(),
        "project_id": project_id,
        "change_kind": change_kind,
        "entity_refs": entity_refs or {},
        "mount_point": MOUNT_AFTER_GRAPH_WRITE,
    }
    if graph is not None:
        payload["project_graph"] = graph

    row = GeObservationOutbox(
        id=uuid.uuid4().hex,
        idempotency_key=key,
        mount_point=MOUNT_AFTER_GRAPH_WRITE,
        payload=payload,
        status="pending",
        attempts=0,
        created_at=now_iso(),
    )
    db.add(row)
    db.flush()
    return [row]


def notify_graph_write(
    db: Session,
    *,
    project_id: str,
    change_kind: str,
    entity_refs: dict[str, Any] | None = None,
    include_graph: bool = True,
) -> None:
    """Enqueue + commit + non-blocking flush. Safe to call after a graph write commit."""
    try:
        enqueue_after_project_graph_write(
            db,
            project_id=project_id,
            change_kind=change_kind,
            entity_refs=entity_refs,
            include_graph=include_graph,
        )
        db.commit()
        schedule_flush_soon()
    except Exception:
        logger.exception("observation_notify_failed project=%s kind=%s", project_id, change_kind)
        try:
            db.rollback()
        except Exception:
            pass


def requeue_dead_outbox(
    db: Session,
    *,
    error_substr: str = "401",
    limit: int = 200,
) -> dict[str, Any]:
    """Reset dead rows whose last_error contains ``error_substr`` back to pending (CODE-005 M4)."""
    needle = (error_substr or "").strip()
    if not needle:
        raise ValueError("error_substr_required")
    rows = (
        db.query(GeObservationOutbox)
        .filter(GeObservationOutbox.status == "dead")
        .order_by(GeObservationOutbox.created_at.asc())
        .limit(limit)
        .all()
    )
    ids: list[str] = []
    for row in rows:
        err = str(row.last_error or "")
        if needle not in err:
            continue
        row.status = "pending"
        row.attempts = 0
        row.last_error = None
        row.delivered_at = None
        db.add(row)
        ids.append(row.id)
    db.flush()
    return {"requeued": len(ids), "ids": ids, "error_substr": needle}


def deliver_pending(db: Session, *, limit: int = 50) -> dict[str, int]:
    pending = (
        db.query(GeObservationOutbox)
        .filter(GeObservationOutbox.status == "pending")
        .order_by(GeObservationOutbox.id)
        .limit(limit)
        .all()
    )
    subs = (
        db.query(GeObservationSubscription)
        .filter(GeObservationSubscription.enabled.is_(True))
        .all()
    )
    delivered = 0
    dead = 0
    for row in pending:
        ok_all = True
        last_err = None
        for sub in subs:
            if sub.mount_point not in {row.mount_point, "project_lifecycle"}:
                continue
            try:
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                if sub.service_token:
                    headers["Authorization"] = f"Bearer {sub.service_token}"
                body = _payload_as_dict(row.payload)
                r = httpx.post(sub.target_url, json=body, headers=headers, timeout=15.0)
                if r.status_code >= 300:
                    ok_all = False
                    last_err = f"{sub.name}:{r.status_code}"
                    tok_len = len((sub.service_token or "").strip())
                    logger.warning(
                        "observation_deliver_http_error status=%s sub=%s tok_len=%s outbox_id=%s",
                        r.status_code,
                        sub.name,
                        tok_len,
                        row.id,
                    )
            except Exception as e:
                ok_all = False
                last_err = f"{sub.name}:{e}"
                logger.exception("observation_deliver_failed")
        row.attempts = int(row.attempts or 0) + 1
        if not subs:
            # no subscribers: mark delivered (persisted for audit; nothing to fan out)
            row.status = "delivered"
            row.delivered_at = now_iso()
            delivered += 1
        elif ok_all:
            row.status = "delivered"
            row.delivered_at = now_iso()
            delivered += 1
        elif row.attempts >= MAX_ATTEMPTS:
            row.status = "dead"
            row.last_error = last_err
            dead += 1
        else:
            row.last_error = last_err
        db.add(row)
    db.flush()
    return {"delivered": delivered, "dead": dead, "attempted": len(pending)}


def _flush_in_new_session() -> None:
    try:
        from app.db import get_session_factory

        factory = get_session_factory()
        db = factory()
        try:
            result = deliver_pending(db)
            db.commit()
            if result.get("attempted"):
                logger.info("observation_flush %s", result)
        except Exception:
            logger.exception("observation_flush_failed")
            db.rollback()
        finally:
            db.close()
    except Exception:
        logger.exception("observation_flush_session_failed")


def schedule_flush_soon() -> None:
    """Fire-and-forget flush in a daemon thread (does not block the request)."""

    def _run() -> None:
        with _flush_lock:
            _flush_in_new_session()

    threading.Thread(target=_run, name="ge-obs-flush", daemon=True).start()


def start_observation_flush_loop(interval_sec: float = FLUSH_INTERVAL_SEC) -> None:
    """Background periodic flush for the GE process lifespan."""
    global _flush_thread
    if _flush_thread is not None and _flush_thread.is_alive():
        return
    _flush_stop.clear()

    def _loop() -> None:
        while not _flush_stop.wait(interval_sec):
            with _flush_lock:
                _flush_in_new_session()

    _flush_thread = threading.Thread(target=_loop, name="ge-obs-flush-loop", daemon=True)
    _flush_thread.start()
    logger.info("observation_flush_loop_started interval=%s", interval_sec)


def stop_observation_flush_loop() -> None:
    _flush_stop.set()
