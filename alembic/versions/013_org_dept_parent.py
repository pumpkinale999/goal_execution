"""Nested org departments via parent_id.

Revision ID: 013_org_dept_parent
Revises: 012_end_sign_route
"""

from __future__ import annotations

from alembic import op

revision = "013_org_dept_parent"
down_revision = "012_end_sign_route"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE org_departments ADD COLUMN parent_id TEXT
          REFERENCES org_departments(id)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE org_departments DROP COLUMN parent_id
        """
    )
