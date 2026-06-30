"""Backfill: move default-chain business content onto formal annual roots.

Revision ID: 021_default_chain_migrate
Revises: 020_ge_strategic_fields
"""

from __future__ import annotations

from alembic import op

revision = "021_default_chain_migrate"
down_revision = "020_ge_strategic_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import text

    from app.services.ge_default_chain_migrate import run_default_chain_migration_backfill

    connection = op.get_bind()
    for table in ("ge_objectives", "ge_programs", "ge_projects"):
        cols = {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}
        if "sort_order" not in cols:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"),
            )
    run_default_chain_migration_backfill(connection, dry_run=False)


def downgrade() -> None:
    pass
