"""Canvas v2: gate_includes, phase_id on gate_items, Start/End system phases.

Revision ID: 007_canvas_v2
Revises: 006_drop_draft_lifecycle
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from alembic import op
from sqlalchemy import text

revision = "007_canvas_v2"
down_revision = "006_drop_draft_lifecycle"
branch_labels = None
depends_on = None


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _table_has_column(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def _bump_phase_sequences(conn, project_id: str) -> None:
    """Shift business phases up by 1 without violating UNIQUE(project_id, sequence)."""
    phases = conn.execute(
        text(
            """
            SELECT id, sequence FROM ge_phases
            WHERE project_id = :pid
            ORDER BY sequence DESC
            """
        ),
        {"pid": project_id},
    ).fetchall()
    for phase_id, seq in phases:
        conn.execute(
            text("UPDATE ge_phases SET sequence = :new_seq WHERE id = :id"),
            {"new_seq": int(seq) + 1, "id": phase_id},
        )


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_has_column(conn, "ge_phases", "is_system"):
        op.execute("ALTER TABLE ge_phases ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ge_gate_gate_item_include (
          gate_id TEXT NOT NULL REFERENCES ge_gates(id),
          gate_item_id TEXT NOT NULL REFERENCES ge_gate_items(id),
          PRIMARY KEY (gate_id, gate_item_id)
        )
        """
    )
    if not _table_has_column(conn, "ge_gate_items", "phase_id"):
        op.execute("ALTER TABLE ge_gate_items ADD COLUMN phase_id TEXT REFERENCES ge_phases(id)")
    if _table_has_column(conn, "ge_gate_items", "gate_id"):
        op.execute(
            """
            UPDATE ge_gate_items SET phase_id = (
              SELECT phase_id FROM ge_gates WHERE ge_gates.id = ge_gate_items.gate_id
            )
            WHERE phase_id IS NULL
            """
        )
        op.execute(
            """
            INSERT OR IGNORE INTO ge_gate_gate_item_include (gate_id, gate_item_id)
            SELECT gate_id, id FROM ge_gate_items WHERE gate_id IS NOT NULL
            """
        )

    projects = conn.execute(text("SELECT id FROM ge_projects WHERE deleted_at IS NULL")).fetchall()
    now = _now_iso()
    for (project_id,) in projects:
        already_migrated = conn.execute(
            text(
                """
                SELECT 1 FROM ge_phases
                WHERE project_id = :pid AND is_system = 1 AND sequence = 0
                LIMIT 1
                """
            ),
            {"pid": project_id},
        ).first()
        if already_migrated:
            continue

        _bump_phase_sequences(conn, project_id)
        start_id = str(uuid.uuid4())
        start_gate_id = str(uuid.uuid4())
        has_progress = conn.execute(
            text(
                """
                SELECT 1 FROM ge_phases
                WHERE project_id = :pid AND status IN ('active', 'completed')
                LIMIT 1
                """
            ),
            {"pid": project_id},
        ).first()
        start_status = "completed" if has_progress else "pending"
        conn.execute(
            text(
                """
                INSERT INTO ge_phases
                  (id, project_id, sequence, name, status, is_system, created_at, updated_at)
                VALUES
                  (:id, :pid, 0, '开始', :status, 1, :now, :now)
                """
            ),
            {"id": start_id, "pid": project_id, "status": start_status, "now": now},
        )
        conn.execute(
            text("INSERT INTO ge_gates (id, phase_id) VALUES (:gid, :pid)"),
            {"gid": start_gate_id, "pid": start_id},
        )
        max_seq = conn.execute(
            text("SELECT MAX(sequence) FROM ge_phases WHERE project_id = :pid"),
            {"pid": project_id},
        ).scalar()
        end_id = str(uuid.uuid4())
        end_gate_id = str(uuid.uuid4())
        end_seq = int(max_seq or 0) + 1
        conn.execute(
            text(
                """
                INSERT INTO ge_phases
                  (id, project_id, sequence, name, status, is_system, created_at, updated_at)
                VALUES
                  (:id, :pid, :seq, '结束', 'pending', 1, :now, :now)
                """
            ),
            {"id": end_id, "pid": project_id, "seq": end_seq, "now": now},
        )
        conn.execute(
            text("INSERT INTO ge_gates (id, phase_id) VALUES (:gid, :pid)"),
            {"gid": end_gate_id, "pid": end_id},
        )
        if start_status == "pending":
            active_exists = conn.execute(
                text(
                    """
                    SELECT 1 FROM ge_phases
                    WHERE project_id = :pid AND sequence > 0 AND status = 'active'
                    LIMIT 1
                    """
                ),
                {"pid": project_id},
            ).first()
            if active_exists:
                conn.execute(
                    text(
                        "UPDATE ge_phases SET status = 'completed', updated_at = :now WHERE id = :id"
                    ),
                    {"id": start_id, "now": now},
                )

    if _table_has_column(conn, "ge_gate_items", "gate_id"):
        op.execute(
            """
            CREATE TABLE ge_gate_items_new (
              id TEXT PRIMARY KEY,
              phase_id TEXT NOT NULL REFERENCES ge_phases(id),
              name TEXT NOT NULL,
              form TEXT NOT NULL,
              status TEXT NOT NULL,
              payload TEXT NOT NULL DEFAULT '{}',
              submitted_by TEXT,
              signed_by TEXT,
              rejected_by TEXT,
              submitted_at TEXT,
              signed_at TEXT,
              rejected_at TEXT,
              reject_reason TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        op.execute(
            """
            INSERT INTO ge_gate_items_new (
              id, phase_id, name, form, status, payload,
              submitted_by, signed_by, rejected_by,
              submitted_at, signed_at, rejected_at, reject_reason,
              created_at, updated_at
            )
            SELECT
              id, phase_id, name, form, status, payload,
              submitted_by, signed_by, rejected_by,
              submitted_at, signed_at, rejected_at, reject_reason,
              created_at, updated_at
            FROM ge_gate_items
            WHERE phase_id IS NOT NULL
            """
        )
        op.execute("DROP TABLE ge_gate_items")
        op.execute("ALTER TABLE ge_gate_items_new RENAME TO ge_gate_items")


def downgrade() -> None:
    pass
