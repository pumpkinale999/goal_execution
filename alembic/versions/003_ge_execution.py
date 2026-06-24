"""P1 execution chain tables (§2.6).

Revision ID: 003_ge_execution
Revises: 002_ge_bootstrap
"""

from __future__ import annotations

from alembic import op

revision = "003_ge_execution"
down_revision = "002_ge_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_projects (
          id TEXT PRIMARY KEY,
          program_id TEXT NOT NULL REFERENCES ge_programs(id),
          name TEXT NOT NULL,
          pm_user_id TEXT NOT NULL,
          created_by_user_id TEXT NOT NULL,
          status TEXT NOT NULL,
          deleted_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_phases (
          id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL REFERENCES ge_projects(id),
          sequence INTEGER NOT NULL,
          name TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(project_id, sequence)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_gates (
          id TEXT PRIMARY KEY,
          phase_id TEXT NOT NULL UNIQUE REFERENCES ge_phases(id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_gate_items (
          id TEXT PRIMARY KEY,
          gate_id TEXT NOT NULL REFERENCES ge_gates(id),
          name TEXT NOT NULL,
          form TEXT NOT NULL,
          status TEXT NOT NULL,
          payload TEXT NOT NULL DEFAULT '{}',
          submitted_by TEXT,
          signed_by TEXT,
          rejected_by TEXT,
          submitted_at TEXT,
          signed_at TEXT,
          rejected_at TEXT,
          reject_reason TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_tasks (
          id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL REFERENCES ge_projects(id),
          phase_id TEXT NOT NULL REFERENCES ge_phases(id),
          assignee_user_id TEXT,
          title TEXT NOT NULL,
          status TEXT NOT NULL,
          started_at TEXT,
          done_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_task_gate_item_produce (
          task_id TEXT NOT NULL REFERENCES ge_tasks(id),
          gate_item_id TEXT NOT NULL UNIQUE REFERENCES ge_gate_items(id),
          PRIMARY KEY (task_id, gate_item_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_task_gate_item_prerequisite (
          task_id TEXT NOT NULL REFERENCES ge_tasks(id),
          gate_item_id TEXT NOT NULL REFERENCES ge_gate_items(id),
          PRIMARY KEY (task_id, gate_item_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_audit_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          actor_user_id TEXT NOT NULL,
          entity_type TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          action TEXT NOT NULL,
          payload TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ge_audit_entity ON ge_audit_events (entity_type, entity_id, created_at)"
    )
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
        "CREATE INDEX IF NOT EXISTS idx_ge_notif_user_read ON ge_execution_notifications (user_id, read_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ge_execution_notifications")
    op.execute("DROP TABLE IF EXISTS ge_audit_events")
    op.execute("DROP TABLE IF EXISTS ge_task_gate_item_prerequisite")
    op.execute("DROP TABLE IF EXISTS ge_task_gate_item_produce")
    op.execute("DROP TABLE IF EXISTS ge_tasks")
    op.execute("DROP TABLE IF EXISTS ge_gate_items")
    op.execute("DROP TABLE IF EXISTS ge_gates")
    op.execute("DROP TABLE IF EXISTS ge_phases")
    op.execute("DROP TABLE IF EXISTS ge_projects")
