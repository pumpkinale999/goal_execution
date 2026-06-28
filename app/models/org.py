"""Organization ORM models (§2.1)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OrgDepartment(Base):
    __tablename__ = "org_departments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    manager_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("org_departments.id"),
        nullable=True,
    )
    department_note_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    parent: Mapped[OrgDepartment | None] = relationship(
        "OrgDepartment",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list[OrgDepartment]] = relationship(
        "OrgDepartment",
        back_populates="parent",
    )
    teams: Mapped[list[OrgTeam]] = relationship(
        "OrgTeam",
        back_populates="department",
        cascade="all, delete-orphan",
    )


class OrgTeam(Base):
    __tablename__ = "org_teams"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    department_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("org_departments.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    lead_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    team_note_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    department: Mapped[OrgDepartment] = relationship("OrgDepartment", back_populates="teams")


class UserOrgMembership(Base):
    __tablename__ = "user_org_memberships"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("org_departments.id"),
        nullable=False,
    )
    team_id: Mapped[str | None] = mapped_column(String, ForeignKey("org_teams.id"), nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class UserOrgProfile(Base):
    __tablename__ = "user_org_profiles"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    primary_membership_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("user_org_memberships.id"),
        nullable=True,
    )
    manager_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    proficiency_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
