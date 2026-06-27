"""SQLAlchemy engine and session."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None
_migrations_applied = False


class Base(DeclarativeBase):
    pass


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        db_path = settings.goal_execution_db_path.expanduser().resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        _engine = create_engine(url, connect_args={"check_same_thread": False})
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
    """Apply Alembic revisions (001–003) to the configured DB."""
    global _migrations_applied
    if _migrations_applied:
        return
    settings = get_settings()
    db_path = settings.goal_execution_db_path.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
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
