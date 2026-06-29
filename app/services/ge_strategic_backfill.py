"""Strategic field backfill for migration 020 and scripts (M29 · §7.5)."""

from __future__ import annotations

from sqlalchemy import text

from app.constants import GE_DEFAULT_OBJECTIVE_ID
from app.services.ge_strategic_period import current_year_bounds, default_sub_period


def _guess_primary_department(connection, owner_user_id: str | None) -> tuple[str | None, bool]:
    if not owner_user_id:
        return None, False
    managed = connection.execute(
        text("SELECT id FROM org_departments WHERE manager_user_id = :uid ORDER BY name"),
        {"uid": owner_user_id},
    ).fetchall()
    if len(managed) == 1:
        return managed[0][0], False
    if len(managed) > 1:
        profile = connection.execute(
            text("SELECT primary_membership_id FROM user_org_profiles WHERE user_id = :uid"),
            {"uid": owner_user_id},
        ).fetchone()
        if profile and profile[0]:
            row = connection.execute(
                text("SELECT department_id FROM user_org_memberships WHERE id = :mid"),
                {"mid": profile[0]},
            ).fetchone()
            if row:
                dept_id = row[0]
                if any(m[0] == dept_id for m in managed):
                    return dept_id, True
                return managed[0][0], True
        return managed[0][0], True
    profile = connection.execute(
        text("SELECT primary_membership_id FROM user_org_profiles WHERE user_id = :uid"),
        {"uid": owner_user_id},
    ).fetchone()
    if profile and profile[0]:
        row = connection.execute(
            text("SELECT department_id FROM user_org_memberships WHERE id = :mid"),
            {"mid": profile[0]},
        ).fetchone()
        if row:
            return row[0], False
    return None, False


def run_strategic_backfill(connection, *, dry_run: bool = False) -> dict[str, int]:
    stats = {"objectives": 0, "programs": 0, "b1": 0}
    y_start, y_end = current_year_bounds()
    gran, q_start, q_end = default_sub_period()

    if not dry_run:
        connection.execute(
            text(
                """
                UPDATE ge_objectives
                SET period_granularity = 'year',
                    period_start = :start,
                    period_end = :end,
                    lifecycle_status = COALESCE(lifecycle_status, 'active')
                WHERE id = :b1
                """
            ),
            {"start": y_start, "end": y_end, "b1": GE_DEFAULT_OBJECTIVE_ID},
        )
    stats["b1"] = 1

    obj_rows = connection.execute(
        text(
            "SELECT id, owner_user_id, is_default, level, period_start FROM ge_objectives"
        )
    ).fetchall()
    for row_id, owner_uid, is_default, level, period_start in obj_rows:
        if is_default:
            continue
        dept_id, needs_conf = _guess_primary_department(connection, owner_uid)
        updates: dict[str, object] = {}
        if dept_id:
            updates["primary_department_id"] = dept_id
            updates["primary_department_needs_confirmation"] = 1 if needs_conf else 0
        if level == "sub" and not period_start:
            updates["period_granularity"] = gran
            updates["period_start"] = q_start
            updates["period_end"] = q_end
        if not updates:
            continue
        if dry_run:
            stats["objectives"] += 1
            continue
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        connection.execute(
            text(f"UPDATE ge_objectives SET {set_clause} WHERE id = :id"),
            {**updates, "id": row_id},
        )
        stats["objectives"] += 1

    prog_rows = connection.execute(
        text("SELECT id, owner_user_id, is_default, period_start FROM ge_programs")
    ).fetchall()
    for row_id, owner_uid, is_default, period_start in prog_rows:
        if is_default:
            continue
        dept_id, needs_conf = _guess_primary_department(connection, owner_uid)
        if not dept_id:
            continue
        if dry_run:
            stats["programs"] += 1
            continue
        connection.execute(
            text(
                """
                UPDATE ge_programs
                SET primary_department_id = :dept,
                    primary_department_needs_confirmation = :needs
                WHERE id = :id
                """
            ),
            {"dept": dept_id, "needs": 1 if needs_conf else 0, "id": row_id},
        )
        stats["programs"] += 1

    return stats
