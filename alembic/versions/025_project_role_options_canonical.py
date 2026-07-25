"""Canonical project role options (5 seeds) · collapse custom roles to member.

Revision ID: 025_project_role_options_canonical
Revises: 024_project_members
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "025_project_role_options_canonical"
down_revision = "024_project_members"
branch_labels = None
depends_on = None

ROLE_PM_ID = "00000000-0000-4000-8000-0000000000c1"
ROLE_MEMBER_ID = "00000000-0000-4000-8000-0000000000c2"
ROLE_PRODUCT_ID = "00000000-0000-4000-8000-0000000000c3"
ROLE_TECH_ID = "00000000-0000-4000-8000-0000000000c4"
ROLE_TEST_ID = "00000000-0000-4000-8000-0000000000c5"
SEED_TS = "2026-07-25T00:00:00Z"

CANONICAL_SEEDS: list[tuple[str, str, str]] = [
    (ROLE_PM_ID, "项目经理", "project_manager"),
    (ROLE_PRODUCT_ID, "产品经理", "product_manager"),
    (ROLE_TECH_ID, "技术设计师", "technical_designer"),
    (ROLE_TEST_ID, "测试设计师", "test_designer"),
    (ROLE_MEMBER_ID, "团队成员", "member"),
]
CANONICAL_IDS = tuple(row[0] for row in CANONICAL_SEEDS)


def _ensure_seed(conn, role_id: str, name: str, slug: str) -> None:
    """Upsert fixed-id seed; absorb same name/slug rows onto the canonical id."""
    conflicts = conn.execute(
        text(
            """
            SELECT id FROM ge_project_role_options
            WHERE id != :id
              AND (name = :name OR (slug IS NOT NULL AND slug = :slug))
            """
        ),
        {"id": role_id, "name": name, "slug": slug},
    ).fetchall()
    for (conflict_id,) in conflicts:
        conn.execute(
            text(
                """
                UPDATE ge_project_role_options
                SET name = :tmp_name, slug = NULL
                WHERE id = :cid
                """
            ),
            {"tmp_name": f"__migrating_{conflict_id}", "cid": conflict_id},
        )

    existing = conn.execute(
        text("SELECT id FROM ge_project_role_options WHERE id = :id"),
        {"id": role_id},
    ).fetchone()
    if existing:
        conn.execute(
            text(
                """
                UPDATE ge_project_role_options
                SET name = :name, slug = :slug
                WHERE id = :id
                """
            ),
            {"id": role_id, "name": name, "slug": slug},
        )
    else:
        conn.execute(
            text(
                """
                INSERT INTO ge_project_role_options (id, name, slug, created_at)
                VALUES (:id, :name, :slug, :ts)
                """
            ),
            {"id": role_id, "name": name, "slug": slug, "ts": SEED_TS},
        )

    for (conflict_id,) in conflicts:
        conn.execute(
            text(
                """
                UPDATE ge_project_members
                SET role_option_id = :new_id
                WHERE role_option_id = :old_id
                """
            ),
            {"new_id": role_id, "old_id": conflict_id},
        )
        conn.execute(
            text("DELETE FROM ge_project_role_options WHERE id = :cid"),
            {"cid": conflict_id},
        )


def upgrade() -> None:
    conn = op.get_bind()
    for role_id, name, slug in CANONICAL_SEEDS:
        _ensure_seed(conn, role_id, name, slug)

    placeholders = ", ".join(f":id{i}" for i in range(len(CANONICAL_IDS)))
    params = {f"id{i}": cid for i, cid in enumerate(CANONICAL_IDS)}
    params["member_id"] = ROLE_MEMBER_ID
    conn.execute(
        text(
            f"""
            UPDATE ge_project_members
            SET role_option_id = :member_id
            WHERE role_option_id NOT IN ({placeholders})
            """
        ),
        params,
    )
    conn.execute(
        text(
            f"""
            DELETE FROM ge_project_role_options
            WHERE id NOT IN ({placeholders})
            """
        ),
        {f"id{i}": cid for i, cid in enumerate(CANONICAL_IDS)},
    )


def downgrade() -> None:
    conn = op.get_bind()
    # Move members off the three added seeds back to member, then drop those options.
    for role_id in (ROLE_PRODUCT_ID, ROLE_TECH_ID, ROLE_TEST_ID):
        conn.execute(
            text(
                """
                UPDATE ge_project_members
                SET role_option_id = :member_id
                WHERE role_option_id = :role_id
                """
            ),
            {"member_id": ROLE_MEMBER_ID, "role_id": role_id},
        )
        conn.execute(
            text("DELETE FROM ge_project_role_options WHERE id = :role_id"),
            {"role_id": role_id},
        )
    conn.execute(
        text(
            """
            UPDATE ge_project_role_options
            SET name = '成员'
            WHERE id = :member_id AND slug = 'member'
            """
        ),
        {"member_id": ROLE_MEMBER_ID},
    )
