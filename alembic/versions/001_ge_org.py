"""P0 org tables (§2.4).

Revision ID: 001_ge_org
Revises:
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op

revision = "001_ge_org"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS org_departments (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          manager_user_id TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS org_teams (
          id TEXT PRIMARY KEY,
          department_id TEXT NOT NULL REFERENCES org_departments(id),
          name TEXT NOT NULL,
          lead_user_id TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_org_profiles (
          user_id TEXT PRIMARY KEY,
          department_id TEXT REFERENCES org_departments(id),
          team_id TEXT REFERENCES org_teams(id),
          manager_user_id TEXT,
          proficiency_level TEXT,
          updated_at TEXT NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_org_profiles")
    op.execute("DROP TABLE IF EXISTS org_teams")
    op.execute("DROP TABLE IF EXISTS org_departments")
