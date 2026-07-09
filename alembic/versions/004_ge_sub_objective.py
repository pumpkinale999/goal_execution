"""Default sub-objective + reparent default program (scheme A).

Revision ID: 004_ge_sub_objective
Revises: 003_ge_execution
"""

from __future__ import annotations

from alembic import op

GE_DEFAULT_OBJECTIVE_ID = "00000000-0000-4000-8000-0000000000b1"
GE_DEFAULT_PROGRAM_ID = "00000000-0000-4000-8000-0000000000b2"
GE_DEFAULT_SUB_OBJECTIVE_ID = "00000000-0000-4000-8000-0000000000b3"
DEFAULT_SUB_OBJECTIVE_NAME = "未分类战略线"

revision = "004_ge_sub_objective"
down_revision = "003_ge_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        f"""
        INSERT OR IGNORE INTO ge_objectives
          (id, name, level, parent_id, owner_user_id, is_default, created_at, updated_at)
        VALUES
          (
            '{GE_DEFAULT_SUB_OBJECTIVE_ID}',
            '{DEFAULT_SUB_OBJECTIVE_NAME}',
            'sub',
            '{GE_DEFAULT_OBJECTIVE_ID}',
            NULL,
            1,
            datetime('now'),
            datetime('now')
          )
        """
    )
    op.execute(
        f"""
        UPDATE ge_programs
        SET objective_id = '{GE_DEFAULT_SUB_OBJECTIVE_ID}',
            updated_at = datetime('now')
        WHERE objective_id = '{GE_DEFAULT_OBJECTIVE_ID}'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE ge_programs
        SET objective_id = '{GE_DEFAULT_OBJECTIVE_ID}',
            updated_at = datetime('now')
        WHERE id = '{GE_DEFAULT_PROGRAM_ID}'
        """
    )
    op.execute(f"DELETE FROM ge_objectives WHERE id = '{GE_DEFAULT_SUB_OBJECTIVE_ID}'")
