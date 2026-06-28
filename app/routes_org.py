"""Organization REST routes (P0 · §4.1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.deps import get_current_user, get_db, require_service_user
from app.models.org import OrgDepartment, OrgTeam, UserOrgMembership, UserOrgProfile
from app.schemas.org import (
    CreateDepartmentRequest,
    CreateOrgMembershipRequest,
    CreateTeamRequest,
    OrgDepartmentOut,
    OrgMemberOut,
    OrgMembershipOut,
    OrgTeamOut,
    PatchDepartmentRequest,
    PatchTeamRequest,
    PatchUserOrgProfileRequest,
    UserOrgProfileOut,
)
from app.services.org_department_tree import department_has_children, department_is_ancestor
from app.services.org_memberships import (
    create_membership,
    delete_membership,
    delete_memberships_for_department,
    delete_memberships_for_team,
    ensure_profile,
    heal_primary_if_single,
    list_memberships_for_user,
    validate_primary_membership_id,
)
from app.services.org_role_membership import ensure_dept_manager_membership, ensure_team_lead_membership

router = APIRouter(prefix="/org", tags=["org"])


def _dept_out(dept: OrgDepartment) -> OrgDepartmentOut:
    return OrgDepartmentOut(
        id=dept.id,
        name=dept.name,
        manager_user_id=dept.manager_user_id,
        parent_id=dept.parent_id,
        teams=[
            OrgTeamOut(id=team.id, name=team.name, lead_user_id=team.lead_user_id)
            for team in sorted(dept.teams, key=lambda t: t.name)
        ],
    )


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _profile_out(db: Session, profile: UserOrgProfile) -> UserOrgProfileOut:
    memberships = list_memberships_for_user(db, profile.user_id)
    return UserOrgProfileOut(
        user_id=profile.user_id,
        primary_membership_id=profile.primary_membership_id,
        memberships=[
            OrgMembershipOut(
                id=m.id,
                user_id=m.user_id,
                department_id=m.department_id,
                team_id=m.team_id,
                is_primary=m.id == profile.primary_membership_id,
            )
            for m in memberships
        ],
        proficiency=profile.proficiency_level,
        manager_user_id=profile.manager_user_id,
    )


def _get_or_create_profile(db: Session, user_id: str, *, now: str) -> UserOrgProfile:
    profile = db.get(UserOrgProfile, user_id)
    if profile is None:
        memberships = list_memberships_for_user(db, user_id)
        if not memberships:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
        profile = ensure_profile(db, user_id, now=now)
    return profile


@router.get("/departments", response_model=list[OrgDepartmentOut])
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(get_current_user)],
) -> list[OrgDepartmentOut]:
    departments = db.query(OrgDepartment).order_by(OrgDepartment.name).all()
    return [_dept_out(dept) for dept in departments]


@router.post("/departments", response_model=OrgDepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    body: CreateDepartmentRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> OrgDepartmentOut:
    parent_id = body.parent_id
    if parent_id is not None:
        parent = db.get(OrgDepartment, parent_id)
        if parent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    now = _now_iso()
    dept = OrgDepartment(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        manager_user_id=body.manager_user_id,
        parent_id=parent_id,
        created_at=now,
        updated_at=now,
    )
    db.add(dept)
    db.flush()
    if body.manager_user_id:
        ensure_dept_manager_membership(
            db,
            department_id=dept.id,
            user_id=body.manager_user_id,
            now=now,
        )
    db.commit()
    db.refresh(dept)
    return _dept_out(dept)


@router.patch("/departments/{department_id}", response_model=OrgDepartmentOut)
def patch_department(
    department_id: str,
    body: PatchDepartmentRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> OrgDepartmentOut:
    dept = db.get(OrgDepartment, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    now = _now_iso()
    if body.name is not None:
        dept.name = body.name.strip()
    if body.manager_user_id is not None or "manager_user_id" in body.model_fields_set:
        dept.manager_user_id = body.manager_user_id
        if dept.manager_user_id:
            ensure_dept_manager_membership(
                db,
                department_id=department_id,
                user_id=dept.manager_user_id,
                now=now,
            )
    if "parent_id" in body.model_fields_set:
        new_parent_id = body.parent_id
        if new_parent_id == department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"detail": "invalid_parent"},
            )
        if new_parent_id is not None:
            parent = db.get(OrgDepartment, new_parent_id)
            if parent is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
            if department_is_ancestor(db, department_id, new_parent_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"detail": "department_cycle"},
                )
        dept.parent_id = new_parent_id
    dept.updated_at = now
    db.commit()
    db.refresh(dept)
    return _dept_out(dept)


@router.post("/teams", response_model=OrgTeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    body: CreateTeamRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> OrgTeamOut:
    dept = db.get(OrgDepartment, body.department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    now = _now_iso()
    team = OrgTeam(
        id=str(uuid.uuid4()),
        department_id=body.department_id,
        name=body.name.strip(),
        lead_user_id=body.lead_user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(team)
    db.flush()
    if body.lead_user_id:
        ensure_team_lead_membership(
            db,
            team_id=team.id,
            department_id=body.department_id,
            user_id=body.lead_user_id,
            now=now,
        )
    db.commit()
    db.refresh(team)
    return OrgTeamOut(id=team.id, name=team.name, lead_user_id=team.lead_user_id)


@router.patch("/teams/{team_id}", response_model=OrgTeamOut)
def patch_team(
    team_id: str,
    body: PatchTeamRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> OrgTeamOut:
    team = db.get(OrgTeam, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    now = _now_iso()
    if body.name is not None:
        team.name = body.name.strip()
    if body.lead_user_id is not None or "lead_user_id" in body.model_fields_set:
        team.lead_user_id = body.lead_user_id
        if team.lead_user_id:
            ensure_team_lead_membership(
                db,
                team_id=team_id,
                department_id=team.department_id,
                user_id=team.lead_user_id,
                now=now,
            )
    team.updated_at = now
    db.commit()
    db.refresh(team)
    return OrgTeamOut(id=team.id, name=team.name, lead_user_id=team.lead_user_id)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: str,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> None:
    team = db.get(OrgTeam, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    now = _now_iso()
    delete_memberships_for_team(db, team_id, now=now)
    db.delete(team)
    db.commit()


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: str,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> None:
    dept = db.get(OrgDepartment, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    if dept.teams:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "department_has_teams"},
        )
    if department_has_children(db, department_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "department_has_children"},
        )
    now = _now_iso()
    delete_memberships_for_department(db, department_id, now=now)
    db.delete(dept)
    db.commit()


@router.get("/members", response_model=list[OrgMemberOut])
def list_org_members(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> list[OrgMemberOut]:
    rows = (
        db.query(UserOrgMembership)
        .order_by(UserOrgMembership.user_id, UserOrgMembership.created_at)
        .all()
    )
    return [
        OrgMemberOut(
            user_id=m.user_id,
            membership_id=m.id,
            department_id=m.department_id,
            team_id=m.team_id,
        )
        for m in rows
    ]


@router.get("/users/{user_id}/profile", response_model=UserOrgProfileOut)
def get_user_profile(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> UserOrgProfileOut:
    if user.auth_method == "jwt" and user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "forbidden"})
    now = _now_iso()
    profile = db.get(UserOrgProfile, user_id)
    if profile is None:
        memberships = list_memberships_for_user(db, user_id)
        if not memberships:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
        profile = ensure_profile(db, user_id, now=now)
    heal_primary_if_single(db, profile, now=now)
    db.commit()
    db.refresh(profile)
    return _profile_out(db, profile)


@router.patch("/users/{user_id}/profile", response_model=UserOrgProfileOut)
def patch_user_profile(
    user_id: str,
    body: PatchUserOrgProfileRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> UserOrgProfileOut:
    now = _now_iso()
    profile = db.get(UserOrgProfile, user_id)
    if profile is None:
        profile = ensure_profile(db, user_id, now=now)
    if body.primary_membership_id is not None or "primary_membership_id" in body.model_fields_set:
        validate_primary_membership_id(db, user_id, body.primary_membership_id)
        profile.primary_membership_id = body.primary_membership_id
    if body.proficiency is not None or "proficiency" in body.model_fields_set:
        profile.proficiency_level = body.proficiency
    if body.manager_user_id is not None or "manager_user_id" in body.model_fields_set:
        profile.manager_user_id = body.manager_user_id
    profile.updated_at = now
    db.commit()
    db.refresh(profile)
    return _profile_out(db, profile)


@router.post(
    "/users/{user_id}/memberships",
    response_model=OrgMembershipOut,
    status_code=status.HTTP_201_CREATED,
)
def post_user_membership(
    user_id: str,
    body: CreateOrgMembershipRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> OrgMembershipOut:
    now = _now_iso()
    membership = create_membership(
        db,
        user_id=user_id,
        department_id=body.department_id,
        team_id=body.team_id,
        now=now,
        primary_membership_id=body.primary_membership_id,
    )
    db.commit()
    db.refresh(membership)
    profile = ensure_profile(db, user_id, now=now)
    return OrgMembershipOut(
        id=membership.id,
        user_id=membership.user_id,
        department_id=membership.department_id,
        team_id=membership.team_id,
        is_primary=membership.id == profile.primary_membership_id,
    )


@router.delete("/memberships/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_membership_route(
    membership_id: str,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> None:
    now = _now_iso()
    delete_membership(db, membership_id, now=now)
    db.commit()
