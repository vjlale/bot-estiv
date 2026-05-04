"""FastAPI entrypoint."""
from __future__ import annotations

import logging

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .routers import (
    admin,
    analytics,
    approvals,
    assets,
    calendar,
    campaigns,
    inbox,
    posts,
    settings as settings_router,
    source_assets,
    webhook,
)

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Bot Estiv API",
    version="0.1.0",
    description="Multiagente de marketing digital para Gardens Wood.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(webhook.router)
app.include_router(posts.router)
app.include_router(approvals.router)
app.include_router(campaigns.router)
app.include_router(analytics.router)
app.include_router(calendar.router)
app.include_router(assets.router)
app.include_router(source_assets.router)
app.include_router(inbox.router)
app.include_router(settings_router.router)
app.mount("/media", StaticFiles(directory="/media"), name="media")


@app.get("/health")
async def health() -> dict:
    import asyncio
    from .db import AsyncSessionLocal
    import redis.asyncio as aioredis
    from sqlalchemy import text

    checks: dict[str, str] = {}

    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "service": settings.app_name,
        "env": settings.app_env,
        "checks": checks,
    }


@app.get("/")
def root() -> dict:
    return {
        "name": "Bot Estiv",
        "tagline": "Diseñado para Durar. Creado para Unir.",
        "docs": "/docs",
    }
