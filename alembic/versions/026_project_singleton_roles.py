"""Singleton project roles: demote duplicates + partial UNIQUE indexes.

Revision ID: 026_project_singleton_roles
Revises: 025_project_role_options_canonical
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "026_project_singleton_roles"
down_revision = "025_project_role_options_canonical"
branch_labels = None
depends_on = None

ROLE_MEMBER_ID = "00000000-0000-4000-8000-0000000000c2"
ROLE_PRODUCT_ID = "00000000-0000-4000-8000-0000000000c3"
ROLE_TECH_ID = "00000000-0000-4000-8000-0000000000c4"
ROLE_TEST_ID = "00000000-0000-4000-8000-0000000000c5"

SINGLETON_IDS = (ROLE_PRODUCT_ID, ROLE_TECH_ID, ROLE_TEST_ID)

INDEXES = (
    ("uq_ge_members_singleton_product", ROLE_PRODUCT_ID),
    ("uq_ge_members_singleton_tech", ROLE_TECH_ID),
    ("uq_ge_members_singleton_test", ROLE_TEST_ID),
)


def _dedupe_singleton(conn, singleton_id: str) -> None:
    rows = conn.execute(
        text(
            """
            SELECT id, project_id, created_at
            FROM ge_project_members
            WHERE role_option_id = :rid
            ORDER BY project_id ASC, created_at ASC, id ASC
            """
        ),
        {"rid": singleton_id},
    ).fetchall()
    keep_by_project: dict[str, str] = {}
    demote_ids: list[str] = []
    for row_id, project_id, _created_at in rows:
        if project_id not in keep_by_project:
            keep_by_project[project_id] = row_id
        else:
            demote_ids.append(row_id)
    for row_id in demote_ids:
        conn.execute(
            text(
                """
                UPDATE ge_project_members
                SET role_option_id = :member_id
                WHERE id = :id
                """
            ),
            {"member_id": ROLE_MEMBER_ID, "id": row_id},
        )


def upgrade() -> None:
    conn = op.get_bind()
    for singleton_id in SINGLETON_IDS:
        _dedupe_singleton(conn, singleton_id)
    for index_name, role_id in INDEXES:
        # SQLite forbids bound parameters in partial-index WHERE clauses.
        conn.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
                ON ge_project_members(project_id)
                WHERE role_option_id = '{role_id}'
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    for index_name, _role_id in INDEXES:
        conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
