"""Sync user_org_profiles when department manager or team lead is appointed."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.org import UserOrgProfile


def _upsert_profile(db: Session, user_id: str, *, now: str) -> UserOrgProfile:
    profile = db.get(UserOrgProfile, user_id)
    if profile is None:
        profile = UserOrgProfile(user_id=user_id, updated_at=now)
        db.add(profile)
    return profile


def ensure_dept_manager_membership(
    db: Session,
    *,
    department_id: str,
    user_id: str | None,
    now: str,
) -> None:
    """Appointee becomes a direct department member (no team). No-op when user_id is None."""
    if not user_id:
        return
    profile = _upsert_profile(db, user_id, now=now)
    profile.department_id = department_id
    profile.team_id = None
    profile.updated_at = now


def ensure_team_lead_membership(
    db: Session,
    *,
    team_id: str,
    department_id: str,
    user_id: str | None,
    now: str,
) -> None:
    """Appointee becomes a member of the team and its department. No-op when user_id is None."""
    if not user_id:
        return
    profile = _upsert_profile(db, user_id, now=now)
    profile.department_id = department_id
    profile.team_id = team_id
    profile.updated_at = now
