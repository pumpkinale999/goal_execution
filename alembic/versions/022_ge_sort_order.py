"""Add sort_order to ge_objectives / ge_programs / ge_projects for sibling ordering.

Revision ID: 022_ge_sort_order
Revises: 021_default_chain_migrate
"""

from __future__ import annotations

from collections import defaultdict

from alembic import op
from sqlalchemy import text

revision = "022_ge_sort_order"
down_revision = "021_default_chain_migrate"
branch_labels = None
depends_on = None


def _backfill_sort_orders(connection, *, table: str, group_col: str, where_clause: str = "") -> None:
    where_sql = f" WHERE {where_clause}" if where_clause else ""
    rows = connection.execute(
        text(f"SELECT id, {group_col}, name FROM {table}{where_sql} ORDER BY {group_col}, name"),
    ).fetchall()
    groups: dict[str | None, list[str]] = defaultdict(list)
    for row in rows:
        groups[row[1]].append(row[0])
    for ids in groups.values():
        for index, row_id in enumerate(ids):
            connection.execute(
                text(f"UPDATE {table} SET sort_order = :sort_order WHERE id = :id"),
                {"sort_order": (index + 1) * 10, "id": row_id},
            )


def upgrade() -> None:
    connection = op.get_bind()
    for table in ("ge_objectives", "ge_programs", "ge_projects"):
        cols = {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}
        if "sort_order" not in cols:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"),
            )
    _backfill_sort_orders(connection, table="ge_objectives", group_col="parent_id")
    _backfill_sort_orders(connection, table="ge_programs", group_col="objective_id")
    _backfill_sort_orders(
        connection,
        table="ge_projects",
        group_col="program_id",
        where_clause="deleted_at IS NULL",
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ge_projects DROP COLUMN sort_order")
    op.execute("ALTER TABLE ge_programs DROP COLUMN sort_order")
    op.execute("ALTER TABLE ge_objectives DROP COLUMN sort_order")
