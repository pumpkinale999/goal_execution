"""Add project_note_id to ge_projects (M19).

Revision ID: 009_project_note
Revises: 008_phase_gate_item_schedule
"""

from __future__ import annotations

from alembic import op

revision = "009_project_note"
down_revision = "008_phase_gate_item_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ge_projects ADD COLUMN project_note_id TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE ge_projects DROP COLUMN project_note_id")
