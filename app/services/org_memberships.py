"""OrgMembership CRUD and primary_membership_id invariant (v2.22/v2.23)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.org import OrgDepartment, OrgTeam, UserOrgMembership, UserOrgProfile


class PrimaryMembershipRequired(Exception):
    """Raised when POST membership would leave user with >=2 rows and no primary."""


def ensure_profile(db: Session, user_id: str, *, now: str) -> UserOrgProfile:
    profile = db.get(UserOrgProfile, user_id)
    if profile is not None:
        return profile
    for pending in db.new:
        if isinstance(pending, UserOrgProfile) and pending.user_id == user_id:
            return pending
    profile = UserOrgProfile(user_id=user_id, updated_at=now)
    db.add(profile)
    return profile


def list_memberships_for_user(db: Session, user_id: str) -> list[UserOrgMembership]:
    return (
        db.query(UserOrgMembership)
        .filter(UserOrgMembership.user_id == user_id)
        .order_by(UserOrgMembership.created_at, UserOrgMembership.id)
        .all()
    )


def _membership_in_dept(db: Session, user_id: str, department_id: str) -> UserOrgMembership | None:
    return (
        db.query(UserOrgMembership)
        .filter(
            UserOrgMembership.user_id == user_id,
            UserOrgMembership.department_id == department_id,
        )
        .first()
    )


def _membership_for_team(db: Session, user_id: str, team_id: str) -> UserOrgMembership | None:
    return (
        db.query(UserOrgMembership)
        .filter(
            UserOrgMembership.user_id == user_id,
            UserOrgMembership.team_id == team_id,
        )
        .first()
    )


def heal_primary_if_single(db: Session, profile: UserOrgProfile, *, now: str) -> None:
    """GET profile: 1 membership without primary → auto set primary."""
    memberships = list_memberships_for_user(db, profile.user_id)
    if len(memberships) == 1 and profile.primary_membership_id is None:
        profile.primary_membership_id = memberships[0].id
        profile.updated_at = now


def validate_primary_membership_id(
    db: Session,
    user_id: str,
    primary_membership_id: str | None,
) -> None:
    if primary_membership_id is None:
        return
    membership = db.get(UserOrgMembership, primary_membership_id)
    if membership is None or membership.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "invalid_primary_membership"},
        )


def _apply_primary_after_change(
    db: Session,
    profile: UserOrgProfile,
    *,
    now: str,
    explicit_primary_id: str | None = None,
) -> None:
    memberships = list_memberships_for_user(db, profile.user_id)
    if not memberships:
        profile.primary_membership_id = None
        profile.updated_at = now
        return
    if explicit_primary_id is not None:
        validate_primary_membership_id(db, profile.user_id, explicit_primary_id)
        profile.primary_membership_id = explicit_primary_id
        profile.updated_at = now
        return
    if len(memberships) == 1:
        profile.primary_membership_id = memberships[0].id
        profile.updated_at = now
        return
    if profile.primary_membership_id:
        still_valid = any(m.id == profile.primary_membership_id for m in memberships)
        if not still_valid:
            profile.primary_membership_id = None
            profile.updated_at = now


def create_membership(
    db: Session,
    *,
    user_id: str,
    department_id: str,
    team_id: str | None,
    now: str,
    primary_membership_id: str | None = None,
    skip_primary_gate: bool = False,
) -> UserOrgMembership:
    if db.get(OrgDepartment, department_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if team_id is not None:
        team = db.get(OrgTeam, team_id)
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
        if team.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"detail": "team_department_mismatch"},
            )
        existing = _membership_for_team(db, user_id, team_id)
        if existing:
            return existing
        dept_row = _membership_in_dept(db, user_id, department_id)
        if dept_row is not None:
            if dept_row.team_id is None:
                # Keep direct membership; append team row (same dept direct + group coexist).
                pass
            elif dept_row.team_id == team_id:
                return dept_row
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"detail": "department_membership_conflict"},
                )
    else:
        dept_row = _membership_in_dept(db, user_id, department_id)
        if dept_row is not None:
            if dept_row.team_id is None:
                return dept_row
            dept_row.team_id = None
            dept_row.updated_at = now
            profile = ensure_profile(db, user_id, now=now)
            _apply_primary_after_change(
                db, profile, now=now, explicit_primary_id=primary_membership_id
            )
            return dept_row

    existing_count = len(list_memberships_for_user(db, user_id))
    profile = ensure_profile(db, user_id, now=now)
    would_be_multi = existing_count >= 1
    if would_be_multi and profile.primary_membership_id is None:
        if primary_membership_id is None and not skip_primary_gate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "primary_membership_required"},
            )
        if primary_membership_id is not None:
            validate_primary_membership_id(db, user_id, primary_membership_id)

    membership = UserOrgMembership(
        id=str(uuid.uuid4()),
        user_id=user_id,
        department_id=department_id,
        team_id=team_id,
        created_at=now,
        updated_at=now,
    )
    db.add(membership)
    db.flush()

    _apply_primary_after_change(
        db, profile, now=now, explicit_primary_id=primary_membership_id
    )
    return membership


def delete_membership(db: Session, membership_id: str, *, now: str) -> None:
    membership = db.get(UserOrgMembership, membership_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    user_id = membership.user_id
    was_primary = False
    profile = db.get(UserOrgProfile, user_id)
    if profile and profile.primary_membership_id == membership_id:
        was_primary = True
    db.delete(membership)
    db.flush()
    if profile is None:
        return
    remaining = list_memberships_for_user(db, user_id)
    if not remaining:
        profile.primary_membership_id = None
    elif was_primary:
        if len(remaining) == 1:
            profile.primary_membership_id = remaining[0].id
        else:
            profile.primary_membership_id = None
    profile.updated_at = now


def delete_memberships_for_department(db: Session, department_id: str, *, now: str) -> None:
    rows = (
        db.query(UserOrgMembership)
        .filter(UserOrgMembership.department_id == department_id)
        .all()
    )
    for row in rows:
        delete_membership(db, row.id, now=now)


def delete_memberships_for_team(db: Session, team_id: str, *, now: str) -> None:
    rows = (
        db.query(UserOrgMembership).filter(UserOrgMembership.team_id == team_id).all()
    )
    for row in rows:
        delete_membership(db, row.id, now=now)


def membership_out(
    membership: UserOrgMembership,
    *,
    primary_membership_id: str | None,
) -> dict:
    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "department_id": membership.department_id,
        "team_id": membership.team_id,
        "is_primary": membership.id == primary_membership_id,
    }
