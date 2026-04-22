"""Inbox: hilos de conversación WhatsApp para el dashboard."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Conversation, Message

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("/conversations")
async def list_conversations(session: AsyncSession = Depends(get_session)):
    stmt = select(Conversation).order_by(Conversation.last_message_at.desc()).limit(100)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(c.id),
            "user_wa_id": c.user_wa_id,
            "thread_id": c.thread_id,
            "last_message_at": c.last_message_at.isoformat(),
        }
        for c in rows
    ]


@router.get("/conversations/{conv_id}/messages")
async def list_messages(conv_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
        .limit(500)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "agent": m.agent,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]
