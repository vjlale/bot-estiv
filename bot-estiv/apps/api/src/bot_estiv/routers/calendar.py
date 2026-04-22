"""Calendario editorial: plan semanal + scheduling."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..agents import campaign_planner
from ..db import get_session
from ..models import Post, PostStatus
from ..schemas import PostOut

router = APIRouter(prefix="/calendar", tags=["calendar"])


class ScheduleBody(BaseModel):
    scheduled_for: datetime


@router.get("/week")
async def get_week():
    plan = await campaign_planner.plan_week()
    return plan.model_dump()


@router.get("/upcoming", response_model=list[PostOut])
async def upcoming(session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Post)
        .options(selectinload(Post.assets))
        .where(Post.status.in_([PostStatus.SCHEDULED, PostStatus.APPROVED]))
        .order_by(Post.scheduled_for.asc().nulls_last())
    )
    return (await session.execute(stmt)).scalars().all()


@router.post("/{post_id}/schedule", response_model=PostOut)
async def schedule_post(
    post_id: uuid.UUID,
    body: ScheduleBody,
    session: AsyncSession = Depends(get_session),
):
    post = (
        await session.execute(
            select(Post).options(selectinload(Post.assets)).where(Post.id == post_id)
        )
    ).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    post.scheduled_for = body.scheduled_for
    post.status = PostStatus.SCHEDULED
    await session.commit()
    await session.refresh(post)
    return post
