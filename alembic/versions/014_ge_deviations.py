"""ge_deviations table and task deviation_id (M22).

Revision ID: 014_ge_deviations
Revises: 013_org_dept_parent
"""

from __future__ import annotations

from alembic import op

revision = "014_ge_deviations"
down_revision = "013_org_dept_parent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_deviations (
          id TEXT PRIMARY KEY,
          gate_item_id TEXT NOT NULL REFERENCES ge_gate_items(id),
          project_id TEXT NOT NULL REFERENCES ge_projects(id),
          status TEXT NOT NULL,
          kind TEXT NOT NULL,
          reason TEXT,
          remediation_plan TEXT,
          remediation_due TEXT,
          remediation_task_id TEXT NOT NULL REFERENCES ge_tasks(id),
          superseded_task_id TEXT NOT NULL REFERENCES ge_tasks(id),
          gate_item_status_at_open TEXT NOT NULL,
          superseded_task_status_at_open TEXT NOT NULL,
          revision INTEGER NOT NULL DEFAULT 0,
          opened_by_user_id TEXT NOT NULL,
          opened_at TEXT NOT NULL,
          activated_at TEXT,
          closed_at TEXT,
          cancelled_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ge_deviations_open_active
          ON ge_deviations(gate_item_id)
          WHERE status IN ('open', 'active')
        """
    )
    op.execute("ALTER TABLE ge_tasks ADD COLUMN deviation_id TEXT REFERENCES ge_deviations(id)")


def downgrade() -> None:
    op.execute("ALTER TABLE ge_tasks DROP COLUMN deviation_id")
    op.execute("DROP INDEX IF EXISTS uq_ge_deviations_open_active")
    op.execute("DROP TABLE IF EXISTS ge_deviations")
