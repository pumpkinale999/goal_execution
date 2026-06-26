"""Goal & execution ORM models (§2.2)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class GeObjective(Base):
    __tablename__ = "ge_objectives"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, ForeignKey("ge_objectives.id"), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    programs: Mapped[list[GeProgram]] = relationship("GeProgram", back_populates="objective")


class GeProgram(Base):
    __tablename__ = "ge_programs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    objective_id: Mapped[str] = mapped_column(String, ForeignKey("ge_objectives.id"), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    objective: Mapped[GeObjective] = relationship("GeObjective", back_populates="programs")
    projects: Mapped[list[GeProject]] = relationship("GeProject", back_populates="program")


class GeProject(Base):
    __tablename__ = "ge_projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    program_id: Mapped[str] = mapped_column(String, ForeignKey("ge_programs.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    pm_user_id: Mapped[str] = mapped_column(String, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    project_note_id: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    program: Mapped[GeProgram] = relationship("GeProgram", back_populates="projects")
    phases: Mapped[list[GePhase]] = relationship(
        "GePhase",
        back_populates="project",
        order_by="GePhase.sequence",
    )
    tasks: Mapped[list[GeTask]] = relationship("GeTask", back_populates="project")


class GePhase(Base):
    __tablename__ = "ge_phases"
    __table_args__ = (UniqueConstraint("project_id", "sequence"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("ge_projects.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    is_system: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    planned_start: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_end: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped[GeProject] = relationship("GeProject", back_populates="phases")
    gate: Mapped[GeGate | None] = relationship("GeGate", back_populates="phase", uselist=False)
    gate_items: Mapped[list[GeGateItem]] = relationship("GeGateItem", back_populates="phase")
    tasks: Mapped[list[GeTask]] = relationship("GeTask", back_populates="phase")


class GeGate(Base):
    __tablename__ = "ge_gates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    phase_id: Mapped[str] = mapped_column(String, ForeignKey("ge_phases.id"), nullable=False, unique=True)

    phase: Mapped[GePhase] = relationship("GePhase", back_populates="gate")


class GeGateGateItemInclude(Base):
    __tablename__ = "ge_gate_gate_item_include"

    gate_id: Mapped[str] = mapped_column(String, ForeignKey("ge_gates.id"), primary_key=True)
    gate_item_id: Mapped[str] = mapped_column(String, ForeignKey("ge_gate_items.id"), primary_key=True)


class GeGateItem(Base):
    __tablename__ = "ge_gate_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    phase_id: Mapped[str] = mapped_column(String, ForeignKey("ge_phases.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    form: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    signed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_due: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    phase: Mapped[GePhase] = relationship("GePhase", back_populates="gate_items")

    @property
    def payload_dict(self) -> dict[str, Any]:
        try:
            data = json.loads(self.payload or "{}")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    @payload_dict.setter
    def payload_dict(self, value: dict[str, Any]) -> None:
        self.payload = json.dumps(value or {})


class GeTask(Base):
    __tablename__ = "ge_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("ge_projects.id"), nullable=False)
    phase_id: Mapped[str] = mapped_column(String, ForeignKey("ge_phases.id"), nullable=False)
    assignee_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    canvas_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deviation_id: Mapped[str | None] = mapped_column(String, ForeignKey("ge_deviations.id"), nullable=True)
    is_system: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    done_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped[GeProject] = relationship("GeProject", back_populates="tasks")
    phase: Mapped[GePhase] = relationship("GePhase", back_populates="tasks")
    deviation: Mapped[GeDeviation | None] = relationship("GeDeviation", foreign_keys=[deviation_id])


class GeDeviation(Base):
    __tablename__ = "ge_deviations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    gate_item_id: Mapped[str] = mapped_column(String, ForeignKey("ge_gate_items.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("ge_projects.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_due: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_task_id: Mapped[str] = mapped_column(String, ForeignKey("ge_tasks.id"), nullable=False)
    superseded_task_id: Mapped[str] = mapped_column(String, ForeignKey("ge_tasks.id"), nullable=False)
    gate_item_status_at_open: Mapped[str] = mapped_column(Text, nullable=False)
    superseded_task_status_at_open: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_by_user_id: Mapped[str] = mapped_column(String, nullable=False)
    opened_at: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class GeTaskGateItemProduce(Base):
    __tablename__ = "ge_task_gate_item_produce"

    task_id: Mapped[str] = mapped_column(String, ForeignKey("ge_tasks.id"), primary_key=True)
    gate_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("ge_gate_items.id"),
        primary_key=True,
        unique=True,
    )


class GeTaskGateItemPrerequisite(Base):
    __tablename__ = "ge_task_gate_item_prerequisite"

    task_id: Mapped[str] = mapped_column(String, ForeignKey("ge_tasks.id"), primary_key=True)
    gate_item_id: Mapped[str] = mapped_column(String, ForeignKey("ge_gate_items.id"), primary_key=True)


class GeAuditEvent(Base):
    __tablename__ = "ge_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
