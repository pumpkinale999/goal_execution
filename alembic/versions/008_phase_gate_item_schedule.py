"""Add planned schedule columns to ge_phases and ge_gate_items.

Revision ID: 008_phase_gate_item_schedule
Revises: 007_canvas_v2
"""

from __future__ import annotations

from alembic import op

revision = "008_phase_gate_item_schedule"
down_revision = "007_canvas_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ge_phases ADD COLUMN planned_start TEXT")
    op.execute("ALTER TABLE ge_phases ADD COLUMN planned_end TEXT")
    op.execute("ALTER TABLE ge_gate_items ADD COLUMN planned_due TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE ge_gate_items DROP COLUMN planned_due")
    op.execute("ALTER TABLE ge_phases DROP COLUMN planned_end")
    op.execute("ALTER TABLE ge_phases DROP COLUMN planned_start")
