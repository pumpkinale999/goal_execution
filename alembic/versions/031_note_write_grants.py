"""031: project note write grants (K29).

Revision ID: 031_note_write_grants
Revises: 030_ge_pmbp_user_id
"""

from __future__ import annotations

from alembic import op

revision = "031_note_write_grants"
down_revision = "030_ge_pmbp_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_project_note_write_grants (
          id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL REFERENCES ge_projects(id),
          note_id TEXT NOT NULL,
          user_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE (project_id, note_id, user_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ge_note_write_grants_project_user "
        "ON ge_project_note_write_grants(project_id, user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ge_note_write_grants_project_note "
        "ON ge_project_note_write_grants(project_id, note_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ge_note_write_grants_project_note")
    op.execute("DROP INDEX IF EXISTS ix_ge_note_write_grants_project_user")
    op.execute("DROP TABLE IF EXISTS ge_project_note_write_grants")
