"""Project members roster + system role options (M37).

Revision ID: 024_project_members
Revises: 023_remove_default_chain
"""

from __future__ import annotations

from alembic import op

revision = "024_project_members"
down_revision = "023_remove_default_chain"
branch_labels = None
depends_on = None

ROLE_PM_ID = "00000000-0000-4000-8000-0000000000c1"
ROLE_MEMBER_ID = "00000000-0000-4000-8000-0000000000c2"
SEED_TS = "2026-07-20T00:00:00Z"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_project_role_options (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          slug TEXT UNIQUE,
          created_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_project_members (
          id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL REFERENCES ge_projects(id),
          user_id TEXT NOT NULL,
          role_option_id TEXT NOT NULL REFERENCES ge_project_role_options(id),
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE (project_id, user_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ge_project_members_project ON ge_project_members(project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ge_project_members_user ON ge_project_members(user_id)"
    )
    op.execute(
        f"""
        INSERT OR IGNORE INTO ge_project_role_options (id, name, slug, created_at)
        VALUES
          ('{ROLE_PM_ID}', '项目经理', 'project_manager', '{SEED_TS}'),
          ('{ROLE_MEMBER_ID}', '成员', 'member', '{SEED_TS}')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ge_project_members_user")
    op.execute("DROP INDEX IF EXISTS ix_ge_project_members_project")
    op.execute("DROP TABLE IF EXISTS ge_project_members")
    op.execute("DROP TABLE IF EXISTS ge_project_role_options")
