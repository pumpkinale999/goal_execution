"""Migrate draft projects to active (drop draft lifecycle).

Revision ID: 006_drop_draft_lifecycle
Revises: 005_ge_task_canvas_order
"""

from __future__ import annotations

from alembic import op

revision = "006_drop_draft_lifecycle"
down_revision = "005_ge_task_canvas_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE ge_projects SET status='active' WHERE status='draft'")
    op.execute(
        """
        UPDATE ge_phases SET status='active'
        WHERE id IN (
            SELECT p.id FROM ge_phases p
            INNER JOIN (
                SELECT project_id, MIN(sequence) AS min_seq
                FROM ge_phases
                GROUP BY project_id
            ) first ON first.project_id = p.project_id AND p.sequence = first.min_seq
            WHERE p.status = 'pending'
        )
        """
    )


def downgrade() -> None:
    pass
