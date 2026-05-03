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


class DimensionSpec(BaseModel):
    """Una dimension con valor y label humano — ej (2.20, "2,20 metros de largo")."""
    value_cm: float = Field(description="Valor numérico en centímetros.")
    label: str = Field(description="Texto a mostrar en la dimension line.")
    axis: Literal["horizontal", "vertical"] = "horizontal"


class StepItem(BaseModel):
    """Un paso de proceso/obra para plantilla numbered_steps."""
    number: int = Field(ge=1, le=9)
    title: str = Field(description="Título corto, 2-4 palabras")
    body: str = Field(description="Descripción del paso, 1-3 oraciones")
    # punto opcional al que apunta la lead-line (normalizado 0-1 sobre el canvas)
    anchor_x: float | None = Field(default=None, ge=0.0, le=1.0)
    anchor_y: float | None = Field(default=None, ge=0.0, le=1.0)


class InfographicData(BaseModel):
    """Datos estructurados para plantillas infográficas (dimensions / numbered_steps).

    Si `dimensions` viene cargado, se usa la plantilla infographic_dimensions.
    Si `steps` viene cargado, se usa la plantilla numbered_steps.
    """
    dimensions: list[DimensionSpec] = Field(default_factory=list)
    steps: list[StepItem] = Field(default_factory=list)
    description: str | None = Field(
        default=None,
        description="Párrafo descriptivo que va en el callout_panel",
    )
    project_label: str | None = Field(
        default=None,
        description="Label del proyecto (ej: 'Cerco 30m — Mendiolaza')",
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
    infographic_data: InfographicData | None = Field(
        default=None,
        description=(
            "Datos estructurados para plantillas infográficas. "
            "Si está cargado, se usa pipeline NB2-clean + template infográfica."
        ),
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
