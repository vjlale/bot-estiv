"""Aprobaciones: cola y decisiones desde el dashboard."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Approval, Post, PostStatus
from ..schemas import ApprovalDecision, ApprovalOut

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
async def list_pending(session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Approval)
        .where(Approval.status == "pending")
        .order_by(Approval.requested_at.desc())
    )
    return (await session.execute(stmt)).scalars().all()


@router.post("/{post_id}/decision", response_model=ApprovalOut)
async def decide(
    post_id: uuid.UUID,
    body: ApprovalDecision,
    session: AsyncSession = Depends(get_session),
):
    approval = (
        await session.execute(
            select(Approval).where(Approval.post_id == post_id, Approval.status == "pending")
        )
    ).scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada o ya resuelta")

    post = (await session.execute(select(Post).where(Post.id == post_id))).scalar_one()

    mapping = {"approve": ("approved", PostStatus.APPROVED),
               "reject": ("rejected", PostStatus.REJECTED),
               "edit": ("edit_requested", PostStatus.DRAFT)}
    app_status, post_status = mapping[body.decision]
    approval.status = app_status
    approval.decided_at = datetime.utcnow()
    approval.decision_reason = body.reason
    post.status = post_status
    await session.commit()
    return approval
