"""Posts: listar, filtrar, detalle."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
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
