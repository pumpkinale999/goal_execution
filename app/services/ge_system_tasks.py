"""System lifecycle tasks and gate items (M20 · Start/End phases)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.constants import (
    SYSTEM_END_GATE_ITEM_NAME,
    SYSTEM_END_SIGN_TASK_TITLE,
    SYSTEM_END_TASK_TITLE,
    SYSTEM_START_GATE_ITEM_NAME,
    SYSTEM_START_TASK_TITLE,
)
from app.models.ge import (
    GeGateItem,
    GePhase,
    GeTask,
    GeTaskGateItemPrerequisite,
    GeTaskGateItemProduce,
)
from app.services.ge_gate_includes_sync import sync_gate_includes_for_phase


def default_system_planned_due(now: str, phase_planned_end: str | None) -> str:
    if phase_planned_end:
        return phase_planned_end
    dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    return (dt.date() + timedelta(days=30)).isoformat()


def is_system_end_sign_task(task: GeTask) -> bool:
    return bool(task.is_system) and task.title == SYSTEM_END_SIGN_TASK_TITLE


def is_protected_system_end_sign_prerequisite(
    db: Session,
    *,
    task_id: str,
    gate_item_id: str,
) -> bool:
    task = db.get(GeTask, task_id)
    item = db.get(GeGateItem, gate_item_id)
    if task is None or item is None:
        return False
    return is_system_end_sign_task(task) and item.is_system and item.name == SYSTEM_END_GATE_ITEM_NAME


def needs_system_start_seed(db: Session, phase_id: str) -> bool:
    """True when start phase is missing the built-in task or gate item."""
    return not (_has_system_start_produce_task(db, phase_id) and _has_system_gate_item(db, phase_id))


def needs_system_end_seed(db: Session, phase_id: str) -> bool:
    """True when end phase is missing the built-in produce task or gate item."""
    return not (_has_system_end_produce_task(db, phase_id) and _has_system_end_gate_item(db, phase_id))


def needs_system_end_sign_route_seed(db: Session, phase_id: str) -> bool:
    """True when end phase is missing the auto-seeded PM sign-route task or edge."""
    end_gi = _find_system_end_gate_item(db, phase_id)
    if end_gi is None:
        return False
    sign_task = _find_system_end_sign_task(db, phase_id)
    if sign_task is None:
        return True
    exists = (
        db.query(GeTaskGateItemPrerequisite)
        .filter(
            GeTaskGateItemPrerequisite.task_id == sign_task.id,
            GeTaskGateItemPrerequisite.gate_item_id == end_gi.id,
        )
        .first()
    )
    return exists is None


def phase_has_lifecycle_content(db: Session, phase_id: str) -> bool:
    """True if phase already has any tasks or gate items."""
    has_tasks = db.query(GeTask).filter(GeTask.phase_id == phase_id).first() is not None
    if has_tasks:
        return True
    return db.query(GeGateItem).filter(GeGateItem.phase_id == phase_id).first() is not None


def _has_system_start_produce_task(db: Session, phase_id: str) -> bool:
    return _find_system_start_produce_task(db, phase_id) is not None


def _has_system_end_produce_task(db: Session, phase_id: str) -> bool:
    return _find_system_end_produce_task(db, phase_id) is not None


def _has_system_gate_item(db: Session, phase_id: str) -> bool:
    return (
        db.query(GeGateItem)
        .filter(GeGateItem.phase_id == phase_id, GeGateItem.is_system.is_(True))
        .first()
        is not None
    )


def _has_system_end_gate_item(db: Session, phase_id: str) -> bool:
    return _find_system_end_gate_item(db, phase_id) is not None


def _find_system_start_produce_task(db: Session, phase_id: str) -> GeTask | None:
    return (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == phase_id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_START_TASK_TITLE,
        )
        .first()
    )


def _find_system_end_produce_task(db: Session, phase_id: str) -> GeTask | None:
    return (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == phase_id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_END_TASK_TITLE,
        )
        .first()
    )


def _find_system_end_sign_task(db: Session, phase_id: str) -> GeTask | None:
    return (
        db.query(GeTask)
        .filter(
            GeTask.phase_id == phase_id,
            GeTask.is_system.is_(True),
            GeTask.title == SYSTEM_END_SIGN_TASK_TITLE,
        )
        .first()
    )


def _find_system_end_gate_item(db: Session, phase_id: str) -> GeGateItem | None:
    return (
        db.query(GeGateItem)
        .filter(
            GeGateItem.phase_id == phase_id,
            GeGateItem.is_system.is_(True),
            GeGateItem.name == SYSTEM_END_GATE_ITEM_NAME,
        )
        .first()
    )


def _bump_non_system_task_orders(db: Session, phase_id: str) -> None:
    for task in db.query(GeTask).filter(GeTask.phase_id == phase_id, GeTask.is_system.is_(False)):
        task.canvas_order += 1


def _ensure_produce_link(db: Session, task_id: str, gate_item_id: str) -> None:
    exists = (
        db.query(GeTaskGateItemProduce)
        .filter(
            GeTaskGateItemProduce.task_id == task_id,
            GeTaskGateItemProduce.gate_item_id == gate_item_id,
        )
        .first()
    )
    if exists is None:
        db.add(GeTaskGateItemProduce(task_id=task_id, gate_item_id=gate_item_id))


def _ensure_prerequisite_link(db: Session, task_id: str, gate_item_id: str) -> None:
    exists = (
        db.query(GeTaskGateItemPrerequisite)
        .filter(
            GeTaskGateItemPrerequisite.task_id == task_id,
            GeTaskGateItemPrerequisite.gate_item_id == gate_item_id,
        )
        .first()
    )
    if exists is None:
        db.add(GeTaskGateItemPrerequisite(task_id=task_id, gate_item_id=gate_item_id))


def _ensure_end_sign_route(
    db: Session,
    *,
    project_id: str,
    pm_user_id: str,
    end_phase_id: str,
    end_gi_id: str,
    now: str,
) -> int:
    """Ensure PM sign-route task and prerequisite edge for 结项复盘. Returns tasks added."""
    sign_task = _find_system_end_sign_task(db, end_phase_id)
    if sign_task is None:
        sign_task_id = str(uuid.uuid4())
        sign_task = GeTask(
            id=sign_task_id,
            project_id=project_id,
            phase_id=end_phase_id,
            assignee_user_id=pm_user_id,
            title=SYSTEM_END_SIGN_TASK_TITLE,
            status="blocked",
            canvas_order=1,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
        db.add(sign_task)
        added = 1
    else:
        if sign_task.assignee_user_id != pm_user_id:
            sign_task.assignee_user_id = pm_user_id
            sign_task.updated_at = now
        added = 0

    _ensure_prerequisite_link(db, sign_task.id, end_gi_id)
    return added


def sync_system_end_sign_task_assignee(db: Session, *, project_id: str, pm_user_id: str, now: str) -> None:
    """Keep 确认结项 assignee aligned with project PM."""
    end_phase = (
        db.query(GePhase)
        .filter(GePhase.project_id == project_id, GePhase.is_system.is_(True))
        .order_by(GePhase.sequence.desc())
        .first()
    )
    if end_phase is None:
        return
    sign_task = _find_system_end_sign_task(db, end_phase.id)
    if sign_task is None:
        return
    if sign_task.assignee_user_id != pm_user_id:
        sign_task.assignee_user_id = pm_user_id
        sign_task.updated_at = now


def _ensure_start_side(
    db: Session,
    *,
    project_id: str,
    pm_user_id: str,
    start_phase_id: str,
    start_gate_id: str,
    now: str,
    legacy_complete: bool,
) -> tuple[int, int]:
    del start_gate_id
    task_count = 0
    gate_item_count = 0
    start_task = _find_system_start_produce_task(db, start_phase_id)
    start_gi = (
        db.query(GeGateItem)
        .filter(GeGateItem.phase_id == start_phase_id, GeGateItem.is_system.is_(True))
        .first()
    )
    if start_task is None:
        _bump_non_system_task_orders(db, start_phase_id)
        start_task_id = str(uuid.uuid4())
        task_status = "done" if legacy_complete else "blocked"
        start_task = GeTask(
            id=start_task_id,
            project_id=project_id,
            phase_id=start_phase_id,
            assignee_user_id=pm_user_id,
            title=SYSTEM_START_TASK_TITLE,
            status=task_status,
            canvas_order=0,
            is_system=True,
            done_at=now if legacy_complete else None,
            created_at=now,
            updated_at=now,
        )
        db.add(start_task)
        task_count += 1
    elif legacy_complete and start_task.status != "done":
        start_task.status = "done"
        start_task.done_at = now
        start_task.updated_at = now

    if start_gi is None:
        start_gi_id = str(uuid.uuid4())
        gi_status = "signed" if legacy_complete else "draft"
        start_gi = GeGateItem(
            id=start_gi_id,
            phase_id=start_phase_id,
            name=SYSTEM_START_GATE_ITEM_NAME,
            form="status",
            status=gi_status,
            payload='{"target_state":"已确认","target_value":true}',
            planned_due=None,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
        db.add(start_gi)
        gate_item_count += 1
    elif legacy_complete and start_gi.status != "signed":
        start_gi.status = "signed"
        start_gi.updated_at = now

    assert start_task is not None and start_gi is not None
    _ensure_produce_link(db, start_task.id, start_gi.id)
    sync_gate_includes_for_phase(db, start_phase_id)
    return task_count, gate_item_count


def _ensure_end_side(
    db: Session,
    *,
    project_id: str,
    pm_user_id: str,
    end_phase_id: str,
    end_gate_id: str,
    now: str,
) -> tuple[int, int]:
    del end_gate_id
    task_count = 0
    gate_item_count = 0
    end_task = _find_system_end_produce_task(db, end_phase_id)
    end_gi = _find_system_end_gate_item(db, end_phase_id)
    if end_task is None:
        _bump_non_system_task_orders(db, end_phase_id)
        end_task_id = str(uuid.uuid4())
        end_task = GeTask(
            id=end_task_id,
            project_id=project_id,
            phase_id=end_phase_id,
            assignee_user_id=pm_user_id,
            title=SYSTEM_END_TASK_TITLE,
            status="blocked",
            canvas_order=0,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
        db.add(end_task)
        task_count += 1

    if end_gi is None:
        end_gi_id = str(uuid.uuid4())
        end_gi = GeGateItem(
            id=end_gi_id,
            phase_id=end_phase_id,
            name=SYSTEM_END_GATE_ITEM_NAME,
            form="status",
            status="draft",
            payload='{"target_state":"已完成","target_value":true}',
            planned_due=None,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
        db.add(end_gi)
        gate_item_count += 1

    assert end_task is not None and end_gi is not None
    _ensure_produce_link(db, end_task.id, end_gi.id)
    task_count += _ensure_end_sign_route(
        db,
        project_id=project_id,
        pm_user_id=pm_user_id,
        end_phase_id=end_phase_id,
        end_gi_id=end_gi.id,
        now=now,
    )
    sync_gate_includes_for_phase(db, end_phase_id)
    return task_count, gate_item_count


def ensure_end_sign_route_for_phase(
    db: Session,
    *,
    project_id: str,
    pm_user_id: str,
    end_phase_id: str,
    now: str,
) -> int:
    """Idempotent backfill for end-phase PM sign route. Returns tasks added."""
    end_gi = _find_system_end_gate_item(db, end_phase_id)
    if end_gi is None:
        return 0
    return _ensure_end_sign_route(
        db,
        project_id=project_id,
        pm_user_id=pm_user_id,
        end_phase_id=end_phase_id,
        end_gi_id=end_gi.id,
        now=now,
    )


def seed_system_lifecycle_graph(
    db: Session,
    *,
    project_id: str,
    pm_user_id: str,
    start_phase_id: str,
    start_gate_id: str,
    end_phase_id: str,
    end_gate_id: str,
    now: str,
    start_phase_planned_end: str | None = None,
    end_phase_planned_end: str | None = None,
    seed_start: bool = True,
    seed_end: bool = True,
    seed_end_sign_route: bool = True,
    legacy_start_complete: bool = False,
) -> dict[str, int]:
    """Ensure built-in Start/End tasks, gate items, produce links, and gate includes."""
    del start_phase_planned_end, end_phase_planned_end
    task_count = 0
    gate_item_count = 0

    if seed_start:
        added_tasks, added_gis = _ensure_start_side(
            db,
            project_id=project_id,
            pm_user_id=pm_user_id,
            start_phase_id=start_phase_id,
            start_gate_id=start_gate_id,
            now=now,
            legacy_complete=legacy_start_complete,
        )
        task_count += added_tasks
        gate_item_count += added_gis

    if seed_end:
        added_tasks, added_gis = _ensure_end_side(
            db,
            project_id=project_id,
            pm_user_id=pm_user_id,
            end_phase_id=end_phase_id,
            end_gate_id=end_gate_id,
            now=now,
        )
        task_count += added_tasks
        gate_item_count += added_gis
    elif seed_end_sign_route:
        task_count += ensure_end_sign_route_for_phase(
            db,
            project_id=project_id,
            pm_user_id=pm_user_id,
            end_phase_id=end_phase_id,
            now=now,
        )

    return {"task_count": task_count, "gate_item_count": gate_item_count}
