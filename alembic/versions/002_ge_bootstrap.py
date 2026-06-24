"""P0b bootstrap seeds (§2.5 · §7.3).

Revision ID: 002_ge_bootstrap
Revises: 001_ge_org
"""

from __future__ import annotations

from alembic import op

from app.constants import (
    DEFAULT_OBJECTIVE_NAME,
    DEFAULT_PROGRAM_NAME,
    GE_DEFAULT_OBJECTIVE_ID,
    GE_DEFAULT_PROGRAM_ID,
)

revision = "002_ge_bootstrap"
down_revision = "001_ge_org"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_objectives (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          level TEXT NOT NULL,
          parent_id TEXT REFERENCES ge_objectives(id),
          owner_user_id TEXT,
          is_default INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_programs (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          objective_id TEXT NOT NULL REFERENCES ge_objectives(id),
          owner_user_id TEXT,
          is_default INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        f"""
        INSERT OR IGNORE INTO ge_objectives
          (id, name, level, parent_id, owner_user_id, is_default, created_at, updated_at)
        VALUES
          ('{GE_DEFAULT_OBJECTIVE_ID}', '{DEFAULT_OBJECTIVE_NAME}', 'company', NULL, NULL, 1, datetime('now'), datetime('now'))
        """
    )
    op.execute(
        f"""
        INSERT OR IGNORE INTO ge_programs
          (id, name, objective_id, owner_user_id, is_default, created_at, updated_at)
        VALUES
          ('{GE_DEFAULT_PROGRAM_ID}', '{DEFAULT_PROGRAM_NAME}', '{GE_DEFAULT_OBJECTIVE_ID}', NULL, 1, datetime('now'), datetime('now'))
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ge_programs")
    op.execute("DROP TABLE IF EXISTS ge_objectives")
