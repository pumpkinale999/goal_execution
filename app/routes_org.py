"""Organization REST routes (P0 · §4.1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.deps import get_current_user, get_db, require_service_user
from app.models.org import OrgDepartment, OrgTeam, UserOrgProfile
from app.schemas.org import (
    CreateDepartmentRequest,
    CreateTeamRequest,
    OrgDepartmentOut,
    OrgMemberOut,
    OrgTeamOut,
    PatchDepartmentRequest,
    PatchTeamRequest,
    PatchUserOrgProfileRequest,
    UserOrgProfileOut,
)
from app.services.org_department_tree import department_has_children

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


def _profile_out(profile: UserOrgProfile) -> UserOrgProfileOut:
    return UserOrgProfileOut(
        user_id=profile.user_id,
        department_id=profile.department_id,
        team_id=profile.team_id,
        proficiency=profile.proficiency_level,
        manager_user_id=profile.manager_user_id,
    )


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
    if body.name is not None:
        dept.name = body.name.strip()
    if body.manager_user_id is not None or "manager_user_id" in body.model_fields_set:
        dept.manager_user_id = body.manager_user_id
    dept.updated_at = _now_iso()
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
    if body.name is not None:
        team.name = body.name.strip()
    if body.lead_user_id is not None or "lead_user_id" in body.model_fields_set:
        team.lead_user_id = body.lead_user_id
    team.updated_at = _now_iso()
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
    for profile in db.query(UserOrgProfile).filter(UserOrgProfile.team_id == team_id).all():
        profile.team_id = None
        profile.department_id = None
        profile.updated_at = now
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
    for profile in db.query(UserOrgProfile).filter(UserOrgProfile.department_id == department_id).all():
        profile.department_id = None
        profile.team_id = None
        profile.updated_at = now
    db.delete(dept)
    db.commit()


@router.get("/members", response_model=list[OrgMemberOut])
def list_org_members(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> list[OrgMemberOut]:
    profiles = db.query(UserOrgProfile).order_by(UserOrgProfile.user_id).all()
    return [
        OrgMemberOut(
            user_id=p.user_id,
            department_id=p.department_id,
            team_id=p.team_id,
        )
        for p in profiles
    ]


@router.get("/users/{user_id}/profile", response_model=UserOrgProfileOut)
def get_user_profile(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> UserOrgProfileOut:
    if user.auth_method == "jwt" and user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "forbidden"})
    profile = db.get(UserOrgProfile, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
    return _profile_out(profile)


@router.patch("/users/{user_id}/profile", response_model=UserOrgProfileOut)
def patch_user_profile(
    user_id: str,
    body: PatchUserOrgProfileRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> UserOrgProfileOut:
    profile = db.get(UserOrgProfile, user_id)
    now = _now_iso()
    if profile is None:
        profile = UserOrgProfile(user_id=user_id, updated_at=now)
        db.add(profile)
    if body.department_id is not None or "department_id" in body.model_fields_set:
        if body.department_id is not None:
            if db.get(OrgDepartment, body.department_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
        profile.department_id = body.department_id
    if body.team_id is not None or "team_id" in body.model_fields_set:
        if body.team_id is not None:
            team = db.get(OrgTeam, body.team_id)
            if team is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "not_found"})
            if profile.department_id and team.department_id != profile.department_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"detail": "team_department_mismatch"},
                )
        profile.team_id = body.team_id
    if body.proficiency is not None or "proficiency" in body.model_fields_set:
        profile.proficiency_level = body.proficiency
    if body.manager_user_id is not None or "manager_user_id" in body.model_fields_set:
        profile.manager_user_id = body.manager_user_id
    profile.updated_at = now
    db.commit()
    db.refresh(profile)
    return _profile_out(profile)
