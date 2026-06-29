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
    from app.services.ge_default_chain_migrate import run_default_chain_migration_backfill

    connection = op.get_bind()
    run_default_chain_migration_backfill(connection, dry_run=False)


def downgrade() -> None:
    pass
