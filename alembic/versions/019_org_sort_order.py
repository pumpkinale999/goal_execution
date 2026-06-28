"""Add sort_order to org_departments / org_teams for sibling ordering.

Revision ID: 019_org_sort_order
Revises: 018_org_charter_notes
"""

from __future__ import annotations

from collections import defaultdict

from alembic import op
from sqlalchemy import text

revision = "019_org_sort_order"
down_revision = "018_org_charter_notes"
branch_labels = None
depends_on = None


def _backfill_sort_orders(connection, *, table: str, group_col: str) -> None:
    rows = connection.execute(
        text(f"SELECT id, {group_col}, name FROM {table} ORDER BY {group_col}, name"),
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
    op.execute("ALTER TABLE org_departments ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE org_teams ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
    connection = op.get_bind()
    _backfill_sort_orders(connection, table="org_departments", group_col="parent_id")
    _backfill_sort_orders(connection, table="org_teams", group_col="department_id")


def downgrade() -> None:
    op.execute("ALTER TABLE org_teams DROP COLUMN sort_order")
    op.execute("ALTER TABLE org_departments DROP COLUMN sort_order")
