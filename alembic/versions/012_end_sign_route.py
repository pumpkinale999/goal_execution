"""Backfill auto-seeded PM sign route for 结项复盘 (M20 extension).

Revision ID: 012_end_sign_route
Revises: 011_gate_includes_phase_sync
"""

from __future__ import annotations

from alembic import op

revision = "012_end_sign_route"
down_revision = "011_gate_includes_phase_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import text

    from app.constants import SYSTEM_END_PHASE_NAME
    from app.db import session_scope
    from app.models.ge import GePhase
    from app.services.ge_graph import now_iso, recompute_gate_and_phases, recompute_task_status
    from app.services.ge_system_tasks import ensure_end_sign_route_for_phase

    with session_scope() as db:
        project_rows = db.execute(
            text(
                "SELECT id, pm_user_id FROM ge_projects WHERE deleted_at IS NULL",
            ),
        ).fetchall()
        now = now_iso()
        for row in project_rows:
            project_id = row[0]
            pm_user_id = row[1]
            end_phase = (
                db.query(GePhase)
                .filter(
                    GePhase.project_id == project_id,
                    GePhase.is_system.is_(True),
                    GePhase.name == SYSTEM_END_PHASE_NAME,
                )
                .first()
            )
            if end_phase is None:
                continue
            ensure_end_sign_route_for_phase(
                db,
                project_id=project_id,
                pm_user_id=pm_user_id,
                end_phase_id=end_phase.id,
                now=now,
            )
            db.execute(
                text("UPDATE ge_projects SET updated_at = :now WHERE id = :id"),
                {"now": now, "id": project_id},
            )
        for row in project_rows:
            recompute_gate_and_phases(db, row[0])
            recompute_task_status(db, row[0])


def downgrade() -> None:
    pass
