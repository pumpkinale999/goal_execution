"""032: drop primary_department_id FK to org_departments (ORG-DEPT-GE-VAL).

Org authority is skstudio; GE stores opaque department id references only.
Production Postgres may already lack these FKs — DROP is idempotent.

Revision ID: 032_drop_dept_org_fk
Revises: 031_note_write_grants

Note: revision id must fit alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "032_drop_dept_org_fk"
down_revision = "031_note_write_grants"
branch_labels = None
depends_on = None


def _drop_fk_on_column(connection, *, table: str, column: str) -> None:
    dialect = connection.dialect.name
    if dialect != "postgresql":
        # SQLite create_all / tests do not enforce the legacy REFERENCES from 020.
        return
    rows = connection.execute(
        text(
            """
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN unnest(con.conkey) WITH ORDINALITY AS cols(attnum, ord) ON true
            JOIN pg_attribute att
              ON att.attrelid = rel.oid AND att.attnum = cols.attnum
            WHERE con.contype = 'f'
              AND nsp.nspname = current_schema()
              AND rel.relname = :table
              AND att.attname = :column
            """
        ),
        {"table": table, "column": column},
    ).fetchall()
    for (conname,) in rows:
        connection.execute(text(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{conname}"'))


def upgrade() -> None:
    connection = op.get_bind()
    for table in ("ge_objectives", "ge_programs"):
        _drop_fk_on_column(connection, table=table, column="primary_department_id")


def downgrade() -> None:
    # Do not re-add FK to org_departments (authority is skstudio).
    pass
