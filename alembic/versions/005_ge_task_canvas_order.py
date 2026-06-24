"""Add canvas_order to ge_tasks for swim-lane layout.

Revision ID: 005_ge_task_canvas_order
Revises: 004_ge_sub_objective
"""

from __future__ import annotations

from alembic import op

revision = "005_ge_task_canvas_order"
down_revision = "004_ge_sub_objective"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ge_tasks ADD COLUMN canvas_order INTEGER NOT NULL DEFAULT 0")
    op.execute(
        """
        UPDATE ge_tasks SET canvas_order = (
            SELECT COUNT(*) - 1 FROM ge_tasks AS t2
            WHERE t2.phase_id = ge_tasks.phase_id AND t2.created_at < ge_tasks.created_at
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ge_tasks DROP COLUMN canvas_order")
