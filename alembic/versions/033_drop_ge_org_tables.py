"""033: DROP GE org_* tables (ORG-DEPT-GE-VAL-F2).

Org authority is skstudio; GE must not retain empty org shells that create_all
could otherwise revive. Models are unregistered from app.models.__init__.

Revision ID: 033_drop_ge_org_tables
Revises: 032_drop_dept_org_fk

Note: revision id must fit alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from alembic import op

revision = "033_drop_ge_org_tables"
down_revision = "032_drop_dept_org_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dependency order: profiles → memberships → teams → departments
    op.execute("DROP TABLE IF EXISTS user_org_profiles")
    op.execute("DROP TABLE IF EXISTS user_org_memberships")
    op.execute("DROP TABLE IF EXISTS org_teams")
    op.execute("DROP TABLE IF EXISTS org_departments")


def downgrade() -> None:
    # Irreversible without full org DDL restore; intentional for F2.
    raise NotImplementedError("033_drop_ge_org_tables is not downgradable")
