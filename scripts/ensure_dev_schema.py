#!/usr/bin/env python3
"""Dev / deploy schema bootstrap for Postgres.

Empty DB (no alembic_version): ORM ``create_all`` + ``alembic stamp head``.
Already at head: no-op.
Behind head: refuse stamp — run ``alembic upgrade head`` first (ORG-DEPT-GE-MAINT C9).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_GE_PERF_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_ge_tasks_project_id ON ge_tasks(project_id)",
    "CREATE INDEX IF NOT EXISTS ix_ge_gate_items_phase_id ON ge_gate_items(phase_id)",
    (
        "CREATE INDEX IF NOT EXISTS ix_ge_deviations_project_status "
        "ON ge_deviations(project_id, status)"
    ),
)


def ensure_perf_indexes(engine) -> None:
    """029 · idempotent graph-load indexes (create_all skips existing tables)."""
    from sqlalchemy import text

    with engine.begin() as conn:
        for stmt in _GE_PERF_INDEXES:
            conn.execute(text(stmt))


def decide_schema_action(*, current: str | None, head_rev: str) -> str:
    """Return 'ok' | 'stamp' | 'refuse'. Pure helper for GE-T280."""
    if current == head_rev:
        return "ok"
    if current is None:
        return "stamp"
    return "refuse"


def main() -> int:
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect, text

    from app.db import Base, get_engine, resolve_database_url
    import app.models  # noqa: F401

    url, is_sqlite = resolve_database_url()
    if is_sqlite:
        print(
            "[ensure_dev_schema] 错误: 需要 Postgres DATABASE_URL，"
            "当前为 sqlite。见 .env.example",
            file=sys.stderr,
        )
        return 1

    engine = get_engine()
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["skip_log_config"] = True
    head_rev = ScriptDirectory.from_config(cfg).get_current_head()

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    current = None
    if "alembic_version" in tables:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            current = row[0] if row else None

    Base.metadata.create_all(bind=engine)
    ensure_perf_indexes(engine)

    action = decide_schema_action(current=current, head_rev=head_rev)
    if action == "ok":
        print(f"[ensure_dev_schema] Postgres OK (head={head_rev}, tables={len(tables)})")
        return 0
    if action == "refuse":
        print(
            f"[ensure_dev_schema] 错误: alembic current={current!r} 落后 head={head_rev!r}；"
            "禁止 stamp 假前进。请先: alembic upgrade head"
            "（生产见 GE_ALEMBIC_UPGRADE / up-prod.sh）",
            file=sys.stderr,
        )
        return 1

    command.stamp(cfg, head_rev)
    print(f"[ensure_dev_schema] create_all + stamp → {head_rev} (was {current!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
