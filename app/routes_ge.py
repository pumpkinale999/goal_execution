"""Goal & execution REST routes (P0b–P1 · §4.2–§4.4)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/ge", tags=["ge"])

# M1: routes land per Milestone M2–M4 (bootstrap · CRUD · orchestrator).
