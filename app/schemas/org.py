"""Organization Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OrgTeamOut(BaseModel):
    id: str
    name: str
    lead_user_id: str | None = None


class OrgDepartmentOut(BaseModel):
    id: str
    name: str
    manager_user_id: str | None = None
    teams: list[OrgTeamOut] = Field(default_factory=list)


class CreateDepartmentRequest(BaseModel):
    name: str
    manager_user_id: str | None = None


class PatchDepartmentRequest(BaseModel):
    name: str | None = None
    manager_user_id: str | None = None


class CreateTeamRequest(BaseModel):
    department_id: str
    name: str
    lead_user_id: str | None = None


class UserOrgProfileOut(BaseModel):
    user_id: str
    department_id: str | None = None
    team_id: str | None = None
    proficiency: str | None = None
    manager_user_id: str | None = None


class PatchUserOrgProfileRequest(BaseModel):
    department_id: str | None = None
    team_id: str | None = None
    proficiency: str | None = None
    manager_user_id: str | None = None
