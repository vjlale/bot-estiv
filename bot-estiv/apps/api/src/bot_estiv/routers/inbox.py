"""Inbox: hilos de conversación WhatsApp/Telegram para el dashboard."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
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


class ReplyRequest(BaseModel):
    text: str


@router.post("/conversations/{conv_id}/reply")
async def reply_to_conversation(
    conv_id: uuid.UUID,
    body: ReplyRequest,
    session: AsyncSession = Depends(get_session),
):
    """Envía un mensaje manual desde el dashboard al usuario (WA o Telegram)."""
    convo = (
        await session.execute(select(Conversation).where(Conversation.id == conv_id))
    ).scalar_one_or_none()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    channel = getattr(convo, "channel", "whatsapp")
    user_id = convo.user_wa_id

    if channel == "telegram":
        from ..tools import telegram as tg_tool
        chat_id_str = user_id.removeprefix("tg:")
        if not chat_id_str.lstrip("-").isdigit():
            raise HTTPException(status_code=422, detail=f"chat_id inválido: {user_id}")
        await tg_tool.send_text(int(chat_id_str), body.text)
    else:
        from ..tools import whatsapp as wa_tool
        wa_tool.send_text(user_id, body.text)

    session.add(
        Message(
            conversation_id=conv_id,
            role="assistant",
            agent="dashboard",
            content=body.text,
        )
    )
    await session.commit()
    return {"ok": True, "channel": channel, "to": user_id}
