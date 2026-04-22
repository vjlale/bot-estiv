"""Biblioteca de assets."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Asset
from ..schemas import AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
async def list_assets(
    kind: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Asset).order_by(Asset.created_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(Asset.kind == kind)
    return (await session.execute(stmt)).scalars().all()
