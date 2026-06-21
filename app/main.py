"""FastAPI application entry (M1 scaffold)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.db import db_ok, init_db
from app.routes_ge import router as ge_router
from app.routes_org import router as org_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="goal_execution", version="0.1.0-m1", lifespan=lifespan)

app.include_router(org_router, prefix=API_PREFIX)
app.include_router(ge_router, prefix=API_PREFIX)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "detail" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})


@app.get(f"{API_PREFIX}/health")
def health() -> dict[str, bool | str]:
    return {
        "ok": db_ok(),
        "db_ok": db_ok(),
        "service": "goal_execution",
    }
