"""Analytics: reportes y KPIs."""
from __future__ import annotations

from fastapi import APIRouter

from ..agents import analytics as analytics_agent
from ..agents import trend_scout

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/weekly")
async def weekly():
    report = await analytics_agent.weekly_report()
    return report.model_dump()


@router.get("/trends")
async def trends():
    report = await trend_scout.scout()
    return report.model_dump()
