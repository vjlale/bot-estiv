"""Posts: listar, filtrar, detalle, agendar y reintentar."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..models import Post, PostStatus
from ..schemas import PostOut

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=list[PostOut])
async def list_posts(
    status: PostStatus | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Post).options(selectinload(Post.assets)).order_by(Post.created_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(Post.status == status)
    rows = (await session.execute(stmt)).scalars().all()
    return rows


@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    post = (
        await session.execute(
            select(Post).options(selectinload(Post.assets)).where(Post.id == post_id)
        )
    ).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    return post


class ScheduleRequest(BaseModel):
    scheduled_for: datetime


@router.post("/{post_id}/schedule", response_model=PostOut)
async def schedule_post(
    post_id: uuid.UUID,
    body: ScheduleRequest,
    session: AsyncSession = Depends(get_session),
):
    """Mueve un post APPROVED → SCHEDULED con la fecha/hora de publicación."""
    post = (
        await session.execute(
            select(Post).options(selectinload(Post.assets)).where(Post.id == post_id)
        )
    ).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    if post.status not in (PostStatus.APPROVED, PostStatus.FAILED):
        raise HTTPException(
            status_code=422,
            detail=f"Solo se pueden agendar posts en estado APPROVED o FAILED (actual: {post.status})",
        )
    post.status = PostStatus.SCHEDULED
    post.scheduled_for = body.scheduled_for
    await session.commit()
    await session.refresh(post)
    return post


@router.post("/{post_id}/retry", response_model=PostOut)
async def retry_post(
    post_id: uuid.UUID,
    body: ScheduleRequest,
    session: AsyncSession = Depends(get_session),
):
    """Reintenta un post FAILED: lo mueve a SCHEDULED con nueva fecha."""
    return await schedule_post(post_id, body, session)
