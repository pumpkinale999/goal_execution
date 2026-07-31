#!/usr/bin/env python3
"""Dev schema bootstrap for Postgres (local / deploy target).

Historical Alembic revisions contain SQLite SQL and must not be replayed.
Always: ORM ``create_all`` + ``alembic stamp head``.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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
    if current == head_rev:
        print(f"[ensure_dev_schema] Postgres OK (head={head_rev}, tables={len(tables)})")
        return 0

    command.stamp(cfg, head_rev)
    print(f"[ensure_dev_schema] create_all + stamp → {head_rev} (was {current!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
