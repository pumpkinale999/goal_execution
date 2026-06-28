"""Organization Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OrgTeamOut(BaseModel):
    id: str
    name: str
    lead_user_id: str | None = None
    team_note_id: str | None = None


class OrgDepartmentOut(BaseModel):
    id: str
    name: str
    manager_user_id: str | None = None
    parent_id: str | None = None
    department_note_id: str | None = None
    teams: list[OrgTeamOut] = Field(default_factory=list)


class CreateDepartmentRequest(BaseModel):
    name: str
    manager_user_id: str | None = None
    parent_id: str | None = None


class PatchDepartmentRequest(BaseModel):
    name: str | None = None
    manager_user_id: str | None = None
    parent_id: str | None = None
    department_note_id: str | None = None


class CreateTeamRequest(BaseModel):
    department_id: str
    name: str
    lead_user_id: str | None = None


class PatchTeamRequest(BaseModel):
    name: str | None = None
    lead_user_id: str | None = None
    team_note_id: str | None = None


class OrgMemberOut(BaseModel):
    user_id: str
    membership_id: str
    department_id: str
    team_id: str | None = None


class OrgMembershipOut(BaseModel):
    id: str
    user_id: str
    department_id: str
    team_id: str | None = None
    is_primary: bool = False


class CreateOrgMembershipRequest(BaseModel):
    department_id: str
    team_id: str | None = None
    primary_membership_id: str | None = None


class UserOrgProfileOut(BaseModel):
    user_id: str
    primary_membership_id: str | None = None
    memberships: list[OrgMembershipOut] = Field(default_factory=list)
    proficiency: str | None = None
    manager_user_id: str | None = None


class PatchUserOrgProfileRequest(BaseModel):
    primary_membership_id: str | None = None
    proficiency: str | None = None
    manager_user_id: str | None = None
