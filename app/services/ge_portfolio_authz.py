"""GE-AUTHZ-API M8 · portfolio authorization from §3.2 org claim headers."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.auth import AuthUser

HDR_PORTFOLIO_DEPTS = "X-Actor-Org-Portfolio-Department-Ids"
HDR_PORTFOLIO_TEAMS = "X-Actor-Org-Portfolio-Team-Ids"
HDR_TARGET_DEPT = "X-Target-Org-Department-Id"
HDR_TARGET_TEAM = "X-Target-Org-Team-Id"


def parse_csv_ids(raw: str | None) -> set[str]:
    if raw is None or not str(raw).strip():
        return set()
    return {part.strip() for part in str(raw).split(",") if part.strip()}


def _forbidden(detail: str = "portfolio_forbidden") -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"detail": detail},
    )


def require_department_portfolio(
    user: AuthUser,
    department_id: str,
    *,
    portfolio_department_ids: str | None,
) -> None:
    if user.is_reviewer:
        return
    allowed = parse_csv_ids(portfolio_department_ids)
    if department_id not in allowed:
        _forbidden()


def require_team_portfolio(
    user: AuthUser,
    team_id: str,
    *,
    portfolio_team_ids: str | None,
) -> None:
    if user.is_reviewer:
        return
    allowed = parse_csv_ids(portfolio_team_ids)
    if team_id not in allowed:
        _forbidden()


def require_user_portfolio(
    user: AuthUser,
    target_user_id: str,
    *,
    portfolio_department_ids: str | None,
    portfolio_team_ids: str | None,
    target_department_id: str | None,
    target_team_id: str | None,
) -> None:
    if user.is_reviewer:
        return
    if str(user.user_id) == str(target_user_id):
        return
    depts = parse_csv_ids(portfolio_department_ids)
    teams = parse_csv_ids(portfolio_team_ids)
    t_dept = (target_department_id or "").strip()
    t_team = (target_team_id or "").strip()
    if t_dept and t_dept in depts:
        return
    if t_team and t_team in teams:
        return
    _forbidden()


def require_migrate_reviewer(user: AuthUser) -> None:
    if not user.is_reviewer:
        _forbidden("reviewer_required")
