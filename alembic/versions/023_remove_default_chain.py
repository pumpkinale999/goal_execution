"""Remove global default chain placeholders (b1/b3/b2).

Revision ID: 023_remove_default_chain
Revises: 022_ge_sort_order
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "023_remove_default_chain"
down_revision = "022_ge_sort_order"
branch_labels = None
depends_on = None

GE_DEFAULT_OBJECTIVE_ID = "00000000-0000-4000-8000-0000000000b1"
GE_DEFAULT_PROGRAM_ID = "00000000-0000-4000-8000-0000000000b2"
GE_DEFAULT_SUB_OBJECTIVE_ID = "00000000-0000-4000-8000-0000000000b3"


def upgrade() -> None:
    conn = op.get_bind()
    active = conn.execute(
        text(
            """
            SELECT count(*) FROM ge_projects
            WHERE program_id = :pid AND deleted_at IS NULL
            """
        ),
        {"pid": GE_DEFAULT_PROGRAM_ID},
    ).scalar()
    if active:
        raise RuntimeError(
            f"Cannot remove default chain: {active} active project(s) still on default program"
        )

    formal = conn.execute(
        text("SELECT id FROM ge_programs WHERE is_default = 0 ORDER BY name LIMIT 1")
    ).scalar()
    if formal:
        conn.execute(
            text(
                """
                UPDATE ge_projects
                SET program_id = :target
                WHERE program_id = :pid
                """
            ),
            {"target": formal, "pid": GE_DEFAULT_PROGRAM_ID},
        )

    conn.execute(
        text("DELETE FROM ge_programs WHERE id = :id"),
        {"id": GE_DEFAULT_PROGRAM_ID},
    )
    conn.execute(
        text("DELETE FROM ge_objectives WHERE id = :id"),
        {"id": GE_DEFAULT_SUB_OBJECTIVE_ID},
    )
    conn.execute(
        text("DELETE FROM ge_objectives WHERE id = :id"),
        {"id": GE_DEFAULT_OBJECTIVE_ID},
    )


def downgrade() -> None:
    # Default chain removal is one-way; historical seeds live in 002/004.
    pass
