"""v2.22/v2.23 · user_org_memberships + primary_membership_id.

Revision ID: 017_org_memberships
Revises: 016_m23_clear_task_legacy_status
"""

from __future__ import annotations

import uuid

from alembic import op
from sqlalchemy import text

revision = "017_org_memberships"
down_revision = "016_m23_clear_task_legacy_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_org_memberships (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          department_id TEXT NOT NULL REFERENCES org_departments(id),
          team_id TEXT REFERENCES org_teams(id),
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_user_org_memberships_user_dept_direct
        ON user_org_memberships(user_id, department_id)
        WHERE team_id IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_user_org_memberships_user_team
        ON user_org_memberships(user_id, team_id)
        WHERE team_id IS NOT NULL
        """
    )

    conn = op.get_bind()
    rows = conn.execute(
        text(
            """
        SELECT user_id, department_id, team_id, updated_at
        FROM user_org_profiles
        WHERE department_id IS NOT NULL
        """
        )
    ).fetchall()
    for row in rows:
        user_id, department_id, team_id, updated_at = row
        membership_id = str(uuid.uuid4())
        conn.execute(
            text(
                """
            INSERT INTO user_org_memberships
              (id, user_id, department_id, team_id, created_at, updated_at)
            VALUES (:id, :user_id, :department_id, :team_id, :created_at, :updated_at)
            """
            ),
            {
                "id": membership_id,
                "user_id": user_id,
                "department_id": department_id,
                "team_id": team_id,
                "created_at": updated_at,
                "updated_at": updated_at,
            },
        )

    op.execute(
        """
        ALTER TABLE user_org_profiles
        ADD COLUMN primary_membership_id TEXT
        REFERENCES user_org_memberships(id)
        """
    )

    # Single membership → auto primary
    conn.execute(
        text(
            """
        UPDATE user_org_profiles
        SET primary_membership_id = (
          SELECT m.id FROM user_org_memberships m
          WHERE m.user_id = user_org_profiles.user_id
          LIMIT 1
        )
        WHERE (
          SELECT COUNT(*) FROM user_org_memberships m
          WHERE m.user_id = user_org_profiles.user_id
        ) = 1
        """
        )
    )

    conn.execute(
        text(
            """
        UPDATE user_org_profiles
        SET primary_membership_id = (
          SELECT m.id FROM user_org_memberships m
          WHERE m.user_id = user_org_profiles.user_id
            AND m.department_id = user_org_profiles.department_id
            AND (
              (user_org_profiles.team_id IS NULL AND m.team_id IS NULL)
              OR m.team_id = user_org_profiles.team_id
            )
          LIMIT 1
        )
        WHERE primary_membership_id IS NULL
          AND department_id IS NOT NULL
          AND (
            SELECT COUNT(*) FROM user_org_memberships m
            WHERE m.user_id = user_org_profiles.user_id
          ) >= 2
        """
        )
    )

    op.execute("ALTER TABLE user_org_profiles DROP COLUMN department_id")
    op.execute("ALTER TABLE user_org_profiles DROP COLUMN team_id")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE user_org_profiles
        ADD COLUMN department_id TEXT REFERENCES org_departments(id)
        """
    )
    op.execute(
        """
        ALTER TABLE user_org_profiles
        ADD COLUMN team_id TEXT REFERENCES org_teams(id)
        """
    )

    conn = op.get_bind()
    profiles = conn.execute(
        text("SELECT user_id, primary_membership_id FROM user_org_profiles")
    ).fetchall()
    for user_id, primary_id in profiles:
        if primary_id:
            row = conn.execute(
                text(
                    """
                    SELECT department_id, team_id FROM user_org_memberships WHERE id = :id
                    """
                ),
                {"id": primary_id},
            ).fetchone()
            if row:
                conn.execute(
                    text(
                        """
                    UPDATE user_org_profiles
                    SET department_id = :department_id, team_id = :team_id
                    WHERE user_id = :user_id
                    """
                    ),
                    {
                        "department_id": row[0],
                        "team_id": row[1],
                        "user_id": user_id,
                    },
                )

    op.execute("ALTER TABLE user_org_profiles DROP COLUMN primary_membership_id")
    op.execute("DROP INDEX IF EXISTS uq_user_org_memberships_user_team")
    op.execute("DROP INDEX IF EXISTS uq_user_org_memberships_user_dept_direct")
    op.execute("DROP TABLE IF EXISTS user_org_memberships")
