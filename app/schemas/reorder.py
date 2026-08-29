"""Shared reorder body (objectives / programs / projects)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReorderRequest(BaseModel):
    direction: str = Field(pattern="^(up|down)$")
