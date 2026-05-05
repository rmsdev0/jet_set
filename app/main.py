from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Deque

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int) -> bool:
        now = time.time()
        window = self._events[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True


rate_limiter = RateLimiter()
app = FastAPI(title="Cartridge & Cast API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_context(request: Request, call_next: Callable):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    auth_header = request.headers.get("authorization")
    session_cookie = request.cookies.get(settings.auth_session_cookie_name)
    client_host = request.client.host if request.client else "unknown"
    key = auth_header or session_cookie or client_host
    limit = settings.authenticated_rate_limit_per_minute if auth_header or session_cookie else settings.public_rate_limit_per_minute
    if request.url.path != "/api/v1/health" and not rate_limiter.allow(key, limit):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded.", "request_id": request_id})
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled-error request_id=%s", getattr(request.state, "request_id", "n/a"), exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error.", "request_id": getattr(request.state, "request_id", None)},
    )


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")


def run() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
