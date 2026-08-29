"""Strategic field backfill for migration 020 and scripts (M29 · §7.5).

ORG-DEPT-GE-MAINT: must not read GE org_* tables (authority = skstudio).
Only fills missing sub-objective period fields; never guesses primary_department_id.
"""

from __future__ import annotations

from sqlalchemy import text

from app.services.ge_strategic_period import default_sub_period


def run_strategic_backfill(connection, *, dry_run: bool = False) -> dict[str, int]:
    stats = {"objectives": 0, "programs": 0}
    gran, q_start, q_end = default_sub_period()
    obj_rows = connection.execute(
        text(
            "SELECT id, owner_user_id, is_default, level, period_start FROM ge_objectives"
        )
    ).fetchall()
    for row_id, owner_uid, is_default, level, period_start in obj_rows:
        _ = owner_uid
        if is_default:
            continue
        updates: dict[str, object] = {}
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

    # Programs: no org-based primary_department guess (tables dropped / authority left).
    return stats
