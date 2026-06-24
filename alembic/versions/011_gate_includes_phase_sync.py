"""Sync gate includes to same-phase gate items only.

Revision ID: 011_gate_includes_phase_sync
Revises: 010_system_tasks
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "011_gate_includes_phase_sync"
down_revision = "010_system_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            DELETE FROM ge_gate_gate_item_include
            WHERE (gate_id, gate_item_id) IN (
              SELECT inc.gate_id, inc.gate_item_id
              FROM ge_gate_gate_item_include inc
              JOIN ge_gates g ON g.id = inc.gate_id
              JOIN ge_gate_items gi ON gi.id = inc.gate_item_id
              WHERE gi.phase_id != g.phase_id
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT OR IGNORE INTO ge_gate_gate_item_include (gate_id, gate_item_id)
            SELECT g.id, gi.id
            FROM ge_phases p
            JOIN ge_gates g ON g.phase_id = p.id
            JOIN ge_gate_items gi ON gi.phase_id = p.id
            """
        )
    )


def downgrade() -> None:
    pass
