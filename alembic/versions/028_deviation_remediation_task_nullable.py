"""028: ge_deviations.remediation_task_id nullable (time-first open).

Revision ID: 028_dev_rem_task_null
Revises: 027_observation_mount
"""

from __future__ import annotations

from alembic import op

revision = "028_dev_rem_task_null"
down_revision = "027_observation_mount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres + SQLite: drop NOT NULL on remediation_task_id (open without task).
    with op.batch_alter_table("ge_deviations") as batch:
        batch.alter_column("remediation_task_id", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("ge_deviations") as batch:
        batch.alter_column("remediation_task_id", nullable=False)
