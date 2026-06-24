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
    from app.constants import SYSTEM_END_PHASE_NAME
    from app.db import session_scope
    from app.models.ge import GePhase, GeProject
    from app.services.ge_graph import now_iso, recompute_gate_and_phases, recompute_task_status
    from app.services.ge_system_tasks import ensure_end_sign_route_for_phase

    with session_scope() as db:
        projects = db.query(GeProject).filter(GeProject.deleted_at.is_(None)).all()
        now = now_iso()
        for project in projects:
            end_phase = (
                db.query(GePhase)
                .filter(
                    GePhase.project_id == project.id,
                    GePhase.is_system.is_(True),
                    GePhase.name == SYSTEM_END_PHASE_NAME,
                )
                .first()
            )
            if end_phase is None:
                continue
            ensure_end_sign_route_for_phase(
                db,
                project_id=project.id,
                pm_user_id=project.pm_user_id,
                end_phase_id=end_phase.id,
                now=now,
            )
            project.updated_at = now
        for project in projects:
            recompute_gate_and_phases(db, project.id)
            recompute_task_status(db, project.id)


def downgrade() -> None:
    pass
