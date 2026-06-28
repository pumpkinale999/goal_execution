"""Sync user_org_memberships when department manager or team lead is appointed."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.org_memberships import create_membership, ensure_profile


def ensure_dept_manager_membership(
    db: Session,
    *,
    department_id: str,
    user_id: str | None,
    now: str,
) -> None:
    """Append direct department membership (skip if exists). Does not change primary."""
    if not user_id:
        return
    create_membership(
        db,
        user_id=user_id,
        department_id=department_id,
        team_id=None,
        now=now,
        skip_primary_gate=True,
    )


def ensure_team_lead_membership(
    db: Session,
    *,
    team_id: str,
    department_id: str,
    user_id: str | None,
    now: str,
) -> None:
    """Append team membership; same-dept direct is replaced with team. Does not change primary."""
    if not user_id:
        return
    create_membership(
        db,
        user_id=user_id,
        department_id=department_id,
        team_id=team_id,
        now=now,
        skip_primary_gate=True,
    )
