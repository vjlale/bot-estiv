"""MetaAdsManager: crea, modifica y monitorea campañas vía Marketing API.

Toda acción que muta estado requiere confirmación del humano a través
del Director (Bot Estiv). Este agente produce un PLAN DE CAMBIOS primero.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..rag import retrieve_brand_context
from ..tools import meta_ads
from .base import build_chain

logger = logging.getLogger(__name__)


class AdsAction(BaseModel):
    kind: Literal["create", "pause", "activate", "update_budget", "duplicate"]
    campaign_id: str | None = None
    name: str | None = None
    objective: str | None = None
    daily_budget_cents: int | None = None
    reason: str


class AdsPlan(BaseModel):
    actions: list[AdsAction] = Field(default_factory=list)
    summary: str
    expected_impact: str


SYSTEM = """Sos el Meta Ads Manager de Gardens Wood.

Tu objetivo: proponer acciones en Meta Marketing API (crear, pausar, activar,
ajustar presupuesto, duplicar) para mejorar CPA/ROAS de la cuenta.

Reglas:
- Nunca reduzcas un presupuesto sin justificación de performance.
- No mezcles objetivos distintos en una misma campaña.
- Usá naming convention: "GW_{{objetivo}}_{{audiencia}}_{{fecha}}".
- Sugerí siempre comenzar en status PAUSED; la activación la decide el humano.
- Para AR, pensar en CABA + GBA + grandes ciudades primero; expandir después.

CONTEXTO DE MARCA:
{brand_context}

ESTADO ACTUAL DE CAMPAÑAS:
{current_state}

Devolvé un AdsPlan con actions (lista de cambios concretos), summary y expected_impact."""


async def plan_changes(user_instruction: str) -> AdsPlan:
    ctx = await retrieve_brand_context("campañas de anuncios Meta Gardens Wood")
    try:
        state = meta_ads.list_campaigns()
    except Exception as exc:
        logger.warning("meta_ads.list_failed", exc_info=exc)
        state = []
    chain = build_chain(
        SYSTEM.format(
            brand_context=ctx,
            current_state=state[:10] if state else "Sin campañas activas.",
        ),
        AdsPlan,
        temperature=0.3,
    )
    return await chain.ainvoke({"input": user_instruction})


def apply_action(action: AdsAction) -> dict[str, Any]:
    """Ejecuta una acción aprobada. Debe invocarse DESPUÉS de confirmación humana."""
    if action.kind == "create":
        if not (action.name and action.objective and action.daily_budget_cents):
            raise ValueError("create requiere name, objective y daily_budget_cents")
        cid = meta_ads.create_campaign(
            action.name,
            objective=action.objective,
            daily_budget_cents=action.daily_budget_cents,
        )
        return {"campaign_id": cid, "status": "paused"}
    if not action.campaign_id:
        raise ValueError(f"La acción '{action.kind}' requiere campaign_id")
    if action.kind == "pause":
        meta_ads.pause_campaign(action.campaign_id)
    elif action.kind == "activate":
        meta_ads.activate_campaign(action.campaign_id)
    elif action.kind == "update_budget":
        if not action.daily_budget_cents:
            raise ValueError("update_budget requiere daily_budget_cents")
        meta_ads.update_daily_budget(action.campaign_id, action.daily_budget_cents)
    elif action.kind == "duplicate":
        if not action.name:
            raise ValueError("duplicate requiere name")
        new_id = meta_ads.duplicate_campaign(action.campaign_id, action.name)
        return {"campaign_id": new_id}
    return {"campaign_id": action.campaign_id, "ok": True}
