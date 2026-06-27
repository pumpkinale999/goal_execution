"""M23 · clear legacy ge_tasks.status (blocked/ready/running/done).

Revision ID: 016_m23_clear_task_legacy_status
Revises: 015_drop_ge_execution_notifications
"""

from __future__ import annotations

from alembic import op

revision = "016_m23_clear_task_legacy_status"
down_revision = "015_drop_ge_execution_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # M23 B′: only `deviated` is a persisted task progress marker; legacy lifecycle
    # values are cleared. started_at/done_at are deprecated alongside start/done routes.
    op.execute(
        """
        UPDATE ge_tasks
        SET status = '',
            started_at = NULL,
            done_at = NULL
        WHERE status IN ('blocked', 'ready', 'running', 'done')
        """
    )


def downgrade() -> None:
    # One-way data cleanup; legacy values cannot be reconstructed.
    pass
