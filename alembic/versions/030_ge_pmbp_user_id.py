"""030: optional pmbp_user_id on objectives and programs (M41).

Revision ID: 030_ge_pmbp_user_id
Revises: 029_ge_graph_perf_idx
"""

from __future__ import annotations

from alembic import op

revision = "030_ge_pmbp_user_id"
down_revision = "029_ge_graph_perf_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ge_objectives ADD COLUMN pmbp_user_id TEXT")
    op.execute("ALTER TABLE ge_programs ADD COLUMN pmbp_user_id TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE ge_programs DROP COLUMN pmbp_user_id")
    op.execute("ALTER TABLE ge_objectives DROP COLUMN pmbp_user_id")
