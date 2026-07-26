"""Internal service routes (BFF / PA helpers)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.deps import get_db, require_service_user
from app.services.ge_project_access import build_project_access_for_user
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


@router.get("/users/{user_id}/project-access")
def internal_user_project_access(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    _svc: Annotated[AuthUser, Depends(require_service_user)],
    all_visible: bool = Query(
        default=False,
        description="When true, return every non-deleted project with role=member (reviewer BFF).",
    ),
) -> dict[str, Any]:
    """K27.6 · batch access table for BFF (service token)."""
    subject = AuthUser(user_id=str(user_id).strip(), auth_method="jwt")
    return build_project_access_for_user(
        db,
        subject,
        force_member_all=bool(all_visible),
    )
