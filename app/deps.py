"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import AuthUser, decode_jwt_user, verify_service_token
from app.config import get_settings
from app.db import get_session_factory

_bearer = HTTPBearer(auto_error=False)


def get_db() -> Session:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    x_actor_user_id: Annotated[str | None, Header(alias="X-Actor-User-Id")] = None,
) -> AuthUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "unauthorized"},
        )
    token = creds.credentials
    settings = get_settings()
    if settings.goal_execution_service_token and token == settings.goal_execution_service_token:
        if not x_actor_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"detail": "unauthorized"},
            )
        verify_service_token(token)
        return AuthUser(user_id=x_actor_user_id, auth_method="service")
    return decode_jwt_user(token)


def require_service_user(
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> AuthUser:
    if user.auth_method != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"detail": "service_token_required"})
    return user
