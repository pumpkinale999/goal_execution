"""Add department_note_id / team_note_id for M28 org charter notes.

Revision ID: 018_org_charter_notes
Revises: 017_org_memberships
"""

from __future__ import annotations

from alembic import op

revision = "018_org_charter_notes"
down_revision = "017_org_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE org_departments ADD COLUMN department_note_id TEXT")
    op.execute("ALTER TABLE org_teams ADD COLUMN team_note_id TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE org_teams DROP COLUMN team_note_id")
    op.execute("ALTER TABLE org_departments DROP COLUMN department_note_id")
