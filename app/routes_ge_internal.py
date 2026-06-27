"""Internal service routes (BFF / PA helpers)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.deps import get_db, require_service_user
from app.services.ge_subtree_governor import is_subtree_governor

router = APIRouter(prefix="/internal/ge", tags=["ge-internal"])


@router.get("/subtree-governor/check")
def check_subtree_governor(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
    user_id: str = Query(...),
    objective_id: str | None = Query(default=None),
    program_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> dict[str, bool]:
    return {
        "is_governor": is_subtree_governor(
            db,
            user_id=user_id,
            objective_id=objective_id,
            program_id=program_id,
            project_id=project_id,
        )
    }
