"""SQLAlchemy engine and session — SQLite or Postgres (M1 · D4/D8)."""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None
_migrations_applied = False


class Base(DeclarativeBase):
    pass


def _env_require_postgres(settings_flag: bool) -> bool:
    raw = os.getenv("REQUIRE_POSTGRES", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return bool(settings_flag)


def resolve_database_url() -> tuple[str, bool]:
    settings = get_settings()
    url = (getattr(settings, "database_url", None) or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required (postgresql+psycopg://...). "
            "Tests may set DATABASE_URL=sqlite:///... with REQUIRE_POSTGRES=0."
        )
    is_sqlite = url.startswith("sqlite")
    require_pg = _env_require_postgres(bool(getattr(settings, "require_postgres", True)))
    if require_pg and is_sqlite:
        raise RuntimeError(
            "PG-01: REQUIRE_POSTGRES is set but database_url is sqlite; "
            "set DATABASE_URL to postgresql+psycopg://..."
        )
    return url, is_sqlite


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url, is_sqlite = resolve_database_url()
        if is_sqlite:
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False, "timeout": 30},
                poolclass=NullPool,
            )
        else:
            _engine = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_timeout=30,
            )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session_factory():
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations() -> None:
    """Apply Alembic revisions to the configured DB."""
    global _migrations_applied
    if _migrations_applied:
        return
    url, _ = resolve_database_url()
    if url.startswith("sqlite"):
        settings = get_settings()
        db_path = settings.goal_execution_db_path.expanduser().resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["skip_log_config"] = True
    command.upgrade(cfg, "head")
    _migrations_applied = True
    logger.info("Alembic migrations applied (head)")


def init_db() -> None:
    """Ensure SQLAlchemy engine is ready (migrations run separately via Alembic CLI)."""
    get_engine()


def db_ok() -> bool:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def reset_engine_cache() -> None:
    global _engine, _SessionLocal, _migrations_applied
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _migrations_applied = False
