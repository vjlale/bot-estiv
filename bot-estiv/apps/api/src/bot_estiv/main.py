"""FastAPI entrypoint."""
from __future__ import annotations

import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import (
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

app = FastAPI(
    title="Bot Estiv API",
    version="0.1.0",
    description="Multiagente de marketing digital para Gardens Wood.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}


@app.get("/")
def root() -> dict:
    return {
        "name": "Bot Estiv",
        "tagline": "Diseñado para Durar. Creado para Unir.",
        "docs": "/docs",
    }
