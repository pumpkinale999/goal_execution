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
    # Default-chain content migration removed; chain deleted in 023_remove_default_chain.
    pass


def downgrade() -> None:
    pass
