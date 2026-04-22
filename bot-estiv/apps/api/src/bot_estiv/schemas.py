"""Esquemas Pydantic para API y contratos entre agentes."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ========== Agente contracts ==========

class CopyDraft(BaseModel):
    title: str = Field(description="Título elegante, máx 80 car.")
    caption: str = Field(description="Descripción/body para el post, tono de marca.")
    hashtags: list[str] = Field(description="Hashtags con #, combinados marca+rubro+local.")
    cta: str | None = Field(default=None, description="Call to action sutil.")


class SlideBrief(BaseModel):
    index: int
    headline: str
    body: str | None = None
    visual_prompt: str = Field(description="Prompt visual para la slide.")
    template: str | None = Field(
        default=None,
        description=(
            "Plantilla de overlay a aplicar. Opciones: editorial_hero, "
            "minimal_stamp, cover_hero, split_60_40, spec_card. "
            "Si es None se elige por rol (apertura=cover_hero, detalle=minimal_stamp, etc.)."
        ),
    )


class DesignBrief(BaseModel):
    format: str = Field(description="ig_feed_portrait | ig_story | carousel | ...")
    pillar: Literal["durabilidad", "diseno", "experiencia"] | None = None
    content_type: Literal["educativo", "promocional", "temporada"] | None = None
    topic: str
    slides: list[SlideBrief] = Field(default_factory=list)
    notes: str | None = None
    default_template: str = Field(
        default="editorial_hero",
        description="Plantilla por defecto si una slide no especifica una.",
    )


class BrandCheckResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=1.0)


class ApprovalRequest(BaseModel):
    post_id: uuid.UUID
    preview_media_urls: list[str]
    caption: str
    to_wa_id: str


# ========== API responses ==========

class PostOut(BaseModel):
    id: uuid.UUID
    title: str
    caption: str
    hashtags: list[str] | None = None
    format: str
    status: str
    pillar: str | None = None
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
    assets: list[AssetOut] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetOut(BaseModel):
    id: uuid.UUID
    kind: str
    url: str
    width: int | None = None
    height: int | None = None
    slide_index: int | None = None

    model_config = {"from_attributes": True}


PostOut.model_rebuild()


class CampaignOut(BaseModel):
    id: uuid.UUID
    name: str
    objective: str
    meta_campaign_id: str | None = None
    daily_budget_cents: int | None = None
    status: str
    metrics_snapshot: dict | None = None

    model_config = {"from_attributes": True}


class ApprovalOut(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    status: str
    requested_at: datetime
    decided_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject", "edit"]
    reason: str | None = None


class WeeklyPlanEntry(BaseModel):
    day: str
    slot: str
    format: str
    pillar: str
    content_type: str
    topic: str


class WeeklyPlan(BaseModel):
    week_of: str
    entries: list[WeeklyPlanEntry]
    summary: str


class AnalyticsReport(BaseModel):
    period: str
    kpis: dict
    top_posts: list[dict]
    recommendations: list[str]
