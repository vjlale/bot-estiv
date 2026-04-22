"""Campañas Meta Ads: listar estado, ejecutar planes aprobados."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..agents.meta_ads_manager import AdsAction, apply_action, plan_changes
from ..tools import meta_ads

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("")
def list_campaigns():
    try:
        return meta_ads.list_campaigns()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/plan")
async def plan(instruction: str):
    p = await plan_changes(instruction)
    return p.model_dump()


@router.post("/apply")
def apply(action: AdsAction):
    try:
        return apply_action(action)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
