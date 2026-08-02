"""Authentication helpers (BFF trust model · GE-AUTHZ-API M1)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.config import get_settings


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    auth_method: str  # jwt | service — channel marker only; not authorization
    is_reviewer: bool = False



def verify_service_token(token: str) -> None:
    settings = get_settings()
    expected = settings.goal_execution_service_token
    if not expected or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "unauthorized"},
        )
