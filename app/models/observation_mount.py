"""GE observation mount: subscriptions + outbox (PRA M4)."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


class GeObservationSubscription(Base):
    __tablename__ = "ge_observation_subscriptions"
    __table_args__ = (UniqueConstraint("name", name="uq_ge_obs_sub_name"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    mount_point: Mapped[str] = mapped_column(String(128), default="after_project_graph_write")
    target_url: Mapped[str] = mapped_column(Text)
    service_token: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(Text, default="")


class GeObservationOutbox(Base):
    __tablename__ = "ge_observation_outbox"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(256), index=True)
    mount_point: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|delivered|dead
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, default="")
    delivered_at: Mapped[str | None] = mapped_column(Text, nullable=True)
