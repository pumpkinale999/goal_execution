"""GE portfolio routes (GE-AUTHZ-API M2/M8 · E2 + §5.4 authz)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.deps import get_db, require_service_user
from app.services.ge_goal_portfolio import (
    get_department_goal_portfolio,
    get_team_goal_portfolio,
    get_user_goal_portfolio,
)
from app.services.ge_pbc_projects import projects_for_users_in_period
from app.services.ge_portfolio_authz import (
    HDR_PORTFOLIO_DEPTS,
    HDR_PORTFOLIO_TEAMS,
    HDR_TARGET_DEPT,
    HDR_TARGET_TEAM,
    require_department_portfolio,
    require_migrate_reviewer,
    require_team_portfolio,
    require_user_portfolio,
)
from app.services.org_department_migrate import migrate_primary_objectives

router = APIRouter(prefix="/ge/portfolios", tags=["ge-portfolios"])


@router.post("/projects-for-users")
def post_projects_for_users(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    """Aggregate projects owned (PM) or managed (goal-subtree) by users in a period window.

    Authz: service actor only; skstudio BFF decides which user_ids are in scope.
    """
    _ = user
    user_ids = body.get("user_ids") or []
    if not isinstance(user_ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_ids_required")
    period_start = body.get("period_start")
    period_end = body.get("period_end")
    if not period_start or not period_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_required")
    include_completed = bool(body.get("include_completed", True))
    projects = projects_for_users_in_period(
        db,
        user_ids=[str(u) for u in user_ids],
        period_start=str(period_start),
        period_end=str(period_end),
        include_completed=include_completed,
    )
    return {
        "period": {"start": str(period_start), "end": str(period_end)},
        "projects": projects,
    }


@router.get("/departments/{department_id}")
def get_department_portfolio(
    department_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
    include_completed: int = Query(default=0, ge=0, le=1),
    include_archived: int = Query(default=0, ge=0, le=1),
    x_actor_org_portfolio_department_ids: Annotated[
        str | None, Header(alias=HDR_PORTFOLIO_DEPTS)
    ] = None,
) -> dict[str, Any]:
    require_department_portfolio(
        user,
        department_id,
        portfolio_department_ids=x_actor_org_portfolio_department_ids,
    )
    return get_department_goal_portfolio(
        db,
        department_id,
        include_completed=bool(include_completed),
        include_archived=bool(include_archived),
    )


@router.get("/teams/{team_id}")
def get_team_portfolio(
    team_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
    include_completed: int = Query(default=0, ge=0, le=1),
    include_archived: int = Query(default=0, ge=0, le=1),
    x_actor_org_portfolio_team_ids: Annotated[
        str | None, Header(alias=HDR_PORTFOLIO_TEAMS)
    ] = None,
) -> dict[str, Any]:
    require_team_portfolio(
        user,
        team_id,
        portfolio_team_ids=x_actor_org_portfolio_team_ids,
    )
    return get_team_goal_portfolio(
        db,
        team_id,
        include_completed=bool(include_completed),
        include_archived=bool(include_archived),
    )


@router.get("/users/{user_id}")
def get_user_portfolio(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
    include_completed: int = Query(default=0, ge=0, le=1),
    include_archived: int = Query(default=0, ge=0, le=1),
    x_actor_org_portfolio_department_ids: Annotated[
        str | None, Header(alias=HDR_PORTFOLIO_DEPTS)
    ] = None,
    x_actor_org_portfolio_team_ids: Annotated[
        str | None, Header(alias=HDR_PORTFOLIO_TEAMS)
    ] = None,
    x_target_org_department_id: Annotated[str | None, Header(alias=HDR_TARGET_DEPT)] = None,
    x_target_org_team_id: Annotated[str | None, Header(alias=HDR_TARGET_TEAM)] = None,
) -> dict[str, Any]:
    require_user_portfolio(
        user,
        user_id,
        portfolio_department_ids=x_actor_org_portfolio_department_ids,
        portfolio_team_ids=x_actor_org_portfolio_team_ids,
        target_department_id=x_target_org_department_id,
        target_team_id=x_target_org_team_id,
    )
    return get_user_goal_portfolio(
        db,
        user_id,
        include_completed=bool(include_completed),
        include_archived=bool(include_archived),
    )


@router.post("/departments/{department_id}/migrate-primary-objectives")
def migrate_department_primary_objectives(
    department_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    require_migrate_reviewer(user)
    target = body.get("target_department_id")
    if not target or not str(target).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "target_department_required"},
        )
    return migrate_primary_objectives(db, department_id, str(target).strip())
