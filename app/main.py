"""FastAPI application entry (GE-AUTHZ-API · routes only under /api/v1/ge/*)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.db import init_db
from app.routes_ge import router as ge_router
from app.routes_ge_portfolios import router as ge_portfolios_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.services.observation_mount import (
        start_observation_flush_loop,
        stop_observation_flush_loop,
    )

    start_observation_flush_loop()
    try:
        yield
    finally:
        stop_observation_flush_loop()


app = FastAPI(title="goal_execution", version="0.2.0-authz", lifespan=lifespan)

# Org authority is skstudio (/api/v1/org). GE routes_org.py is unmounted legacy.
# M2: only /api/v1/ge/* (including health, portfolios, check, users project-access).
app.include_router(ge_router, prefix=API_PREFIX)
app.include_router(ge_portfolios_router, prefix=API_PREFIX)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "detail" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})
