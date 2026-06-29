"""M29 strategic fields on ge_objectives / ge_programs.

Revision ID: 020_ge_strategic_fields
Revises: 019_org_sort_order
"""

from __future__ import annotations

from alembic import op

revision = "020_ge_strategic_fields"
down_revision = "019_org_sort_order"
branch_labels = None
depends_on = None

_STRATEGIC_COLUMNS = """
ALTER TABLE {table} ADD COLUMN period_granularity TEXT;
ALTER TABLE {table} ADD COLUMN period_start TEXT;
ALTER TABLE {table} ADD COLUMN period_end TEXT;
ALTER TABLE {table} ADD COLUMN lifecycle_status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE {table} ADD COLUMN primary_department_id TEXT REFERENCES org_departments(id);
ALTER TABLE {table} ADD COLUMN primary_department_needs_confirmation INTEGER NOT NULL DEFAULT 0;
"""


def upgrade() -> None:
    for table in ("ge_objectives", "ge_programs"):
        for stmt in _STRATEGIC_COLUMNS.format(table=table).strip().split("\n"):
            op.execute(stmt)

    from app.services.ge_strategic_backfill import run_strategic_backfill

    connection = op.get_bind()
    run_strategic_backfill(connection, dry_run=False)


def downgrade() -> None:
    for table in ("ge_programs", "ge_objectives"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN primary_department_needs_confirmation")
        op.execute(f"ALTER TABLE {table} DROP COLUMN primary_department_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN lifecycle_status")
        op.execute(f"ALTER TABLE {table} DROP COLUMN period_end")
        op.execute(f"ALTER TABLE {table} DROP COLUMN period_start")
        op.execute(f"ALTER TABLE {table} DROP COLUMN period_granularity")
