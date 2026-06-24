"""Add is_system to ge_tasks and ge_gate_items (M20).

Revision ID: 010_system_tasks
Revises: 009_project_note
"""

from __future__ import annotations

from alembic import op

revision = "010_system_tasks"
down_revision = "009_project_note"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ge_tasks ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE ge_gate_items ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE ge_gate_items DROP COLUMN is_system")
    op.execute("ALTER TABLE ge_tasks DROP COLUMN is_system")
