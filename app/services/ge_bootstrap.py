"""Legacy bootstrap hook — default chain removed in migration 023."""

from __future__ import annotations

from sqlalchemy.orm import Session


def ensure_ge_bootstrap(db: Session) -> None:
    """No-op: global default chain (b1/b3/b2) was removed."""
    del db
