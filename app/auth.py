"""Authentication helpers (BFF trust model · §1.4)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import get_settings


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    auth_method: str  # jwt | service


def decode_jwt_user(token: str) -> AuthUser:
    settings = get_settings()
    secret = settings.goal_execution_jwt_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "misconfigured"},
        )
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.goal_execution_jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "unauthorized"},
        ) from exc
    uid = payload.get("uid") or payload.get("sub")
    if isinstance(uid, int):
        uid = str(uid)
    if not isinstance(uid, str) or not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "unauthorized"},
        )
    return AuthUser(user_id=uid, auth_method="jwt")


def verify_service_token(token: str) -> None:
    settings = get_settings()
    expected = settings.goal_execution_service_token
    if not expected or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "unauthorized"},
        )
