"""Organization REST routes (P0 · §4.1)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/org", tags=["org"])

# M1: routes land in Milestone M1 (001_ge_org migration + GET /departments).
