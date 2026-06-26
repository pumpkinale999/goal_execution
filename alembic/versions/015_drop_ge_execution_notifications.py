"""Drop ge_execution_notifications (GE REST-only refactor).

Revision ID: 015_drop_ge_execution_notifications
Revises: 014_ge_deviations
"""

from __future__ import annotations

from alembic import op

revision = "015_drop_ge_execution_notifications"
down_revision = "014_ge_deviations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ge_execution_notifications")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_execution_notifications (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          project_id TEXT NOT NULL REFERENCES ge_projects(id),
          phase_id TEXT REFERENCES ge_phases(id),
          gate_id TEXT REFERENCES ge_gates(id),
          payload TEXT NOT NULL,
          read_at TEXT,
          created_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ge_notif_user_read "
        "ON ge_execution_notifications (user_id, read_at)"
    )
