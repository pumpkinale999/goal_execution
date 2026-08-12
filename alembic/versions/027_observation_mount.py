"""027: GE observation mount subscriptions + outbox (PRA M4).

Revision ID: 027_observation_mount
Revises: 026_project_singleton_roles
"""

from __future__ import annotations

from alembic import op

revision = "027_observation_mount"
down_revision = "026_project_singleton_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_observation_subscriptions (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          mount_point TEXT NOT NULL DEFAULT 'after_project_graph_write',
          target_url TEXT NOT NULL,
          service_token TEXT NOT NULL DEFAULT '',
          enabled BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_observation_outbox (
          id TEXT PRIMARY KEY,
          idempotency_key TEXT NOT NULL,
          mount_point TEXT NOT NULL,
          payload TEXT,
          status TEXT NOT NULL DEFAULT 'pending',
          attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT,
          created_at TEXT NOT NULL DEFAULT '',
          delivered_at TEXT
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ge_obs_outbox_key ON ge_observation_outbox(idempotency_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ge_obs_outbox_status ON ge_observation_outbox(status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ge_observation_outbox")
    op.execute("DROP TABLE IF EXISTS ge_observation_subscriptions")
