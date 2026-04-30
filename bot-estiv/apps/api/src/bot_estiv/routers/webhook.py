"""Webhook de Twilio WhatsApp.

Verifica firma X-Twilio-Signature, parsea el mensaje, persiste en DB,
invoca el grafo LangGraph y devuelve TwiML vacío (las respuestas salen
por la API de Twilio, no inline).

Además: si el mensaje trae fotos las guarda como SourceAssets. El
`project_tag` se extrae del caption buscando un hashtag (`#proyecto-foo`).
"""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, Response
from sqlalchemy import select

from ..config import settings
from ..db import AsyncSessionLocal
from ..graph import run_graph
from ..models import Conversation, Message, Tenant
from ..routers.source_assets import create_source_asset
from ..tools import storage, telegram, whatsapp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


TWIML_OK = Response(
    content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    media_type="application/xml",
)


async def _ensure_conversation(
    tenant_id, user_id: str, channel: str = "whatsapp"
) -> Conversation:
    async with AsyncSessionLocal() as session:
        convo = (
            await session.execute(
                select(Conversation).where(Conversation.user_wa_id == user_id)
            )
        ).scalar_one_or_none()
        if convo is None:
            convo = Conversation(
                tenant_id=tenant_id,
                channel=channel,
                user_wa_id=user_id,
                thread_id=f"{channel}:{user_id}",
            )
            session.add(convo)
            await session.commit()
            await session.refresh(convo)
        return convo


async def _log_message(convo_id, role: str, content: str, agent: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            Message(
                conversation_id=convo_id,
                role=role,
                agent=agent,
                content=content,
            )
        )
        await session.commit()


_PROJECT_TAG_RE = re.compile(r"#([a-z0-9][a-z0-9\-_]{1,63})", re.IGNORECASE)


def _extract_project_tag(text: str) -> str | None:
    """Devuelve el primer hashtag del texto normalizado (`cerco-mendiolaza`)."""
    if not text:
        return None
    m = _PROJECT_TAG_RE.search(text)
    if not m:
        return None
    return m.group(1).lower()


async def _ingest_photos(incoming, project_tag: str | None) -> list[str]:
    """Descarga cada media, la sube a storage y crea SourceAssets.
    Devuelve la lista de URLs guardadas.
    """
    saved_urls: list[str] = []
    for i, media_url in enumerate(incoming.media_urls):
        try:
            raw = await whatsapp.download_media(media_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "whatsapp.media_download_failed",
                extra={"url": media_url, "err": str(exc)},
            )
            continue
        key = storage.new_key(f"source-assets/whatsapp/{project_tag or 'untagged'}", "jpg")
        url = storage.upload_bytes(raw, key, content_type="image/jpeg")

        width = height = None
        try:
            from PIL import Image
            import io as _io
            img = Image.open(_io.BytesIO(raw))
            width, height = img.size
        except Exception:  # noqa: BLE001
            pass

        await create_source_asset(
            url=url,
            kind="image",
            source_channel="whatsapp",
            project_tag=project_tag,
            caption=incoming.body or None,
            uploaded_by_wa_id=incoming.from_wa,
            width=width,
            height=height,
            metadata={"twilio_media_url": media_url, "sid": incoming.message_sid},
        )
        saved_urls.append(url)
    return saved_urls


async def _handle(form: dict, base_url: str, signature: str | None) -> None:
    if settings.app_env != "development":
        if not signature or not whatsapp.validate_twilio_signature(base_url, form, signature):
            logger.warning("twilio.signature_invalid", extra={"url": base_url})
            return

    incoming = whatsapp.parse_incoming(form)
    logger.info(
        "whatsapp.incoming",
        extra={
            "from": incoming.from_wa,
            "body": incoming.body[:120],
            "num_media": incoming.num_media,
        },
    )

    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(slug=settings.tenant_id, name="Gardens Wood")
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
        tenant_id = tenant.id

    convo = await _ensure_conversation(tenant_id, incoming.from_wa, channel="whatsapp")
    await _log_message(convo.id, "user", incoming.body or f"[{incoming.num_media} media]")

    # --- Si vinieron fotos: ingesta + confirmación, sin llamar al graph ---
    if incoming.num_media > 0:
        project_tag = _extract_project_tag(incoming.body)
        saved = await _ingest_photos(incoming, project_tag)
        if saved:
            tag_str = f"#{project_tag}" if project_tag else "(sin tag)"
            msg = (
                f"Recibí {len(saved)} foto(s) para el proyecto {tag_str}. "
                "Las podés ver en la biblioteca del dashboard."
            )
            if not project_tag:
                msg += (
                    "\n\nPara agrupar este set como proyecto, respondé con un "
                    "hashtag, ej: #cerco-mendiolaza"
                )
            else:
                msg += (
                    f"\n\nCuando tengas todo el set listo, decime: "
                    f"*generá carrusel {project_tag}* y te armo la pieza."
                )
            try:
                whatsapp.send_text(incoming.from_wa, msg)
                await _log_message(convo.id, "assistant", msg, agent="photo_ingester")
            except Exception as exc:  # noqa: BLE001
                logger.warning("whatsapp.reply_failed", exc_info=exc)
            return

    # --- Si era solo texto: flujo normal con el graph ---
    try:
        result = await run_graph(incoming.body, incoming.from_wa, channel="whatsapp")
    except Exception as exc:
        logger.exception("graph.failed")
        whatsapp.send_text(
            incoming.from_wa,
            f"Uy, se me cruzaron los cables. Probá de nuevo. ({type(exc).__name__})",
        )
        return

    reply = result.get("reply_text", "Listo.")
    await _log_message(convo.id, "assistant", reply, agent="director")
    try:
        whatsapp.send_text(incoming.from_wa, reply)
    except Exception as exc:
        logger.warning("whatsapp.reply_failed", exc_info=exc)


@router.post("/twilio", response_class=Response)
async def twilio_webhook(
    request: Request,
    bg: BackgroundTasks,
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
):
    form = dict((await request.form()))
    base_url = str(request.url)

    if not form.get("From"):
        raise HTTPException(status_code=400, detail="Mensaje inválido")

    bg.add_task(_handle, form, base_url, x_twilio_signature)
    return TWIML_OK


# ==========  Telegram  ==========


async def _ingest_tg_photos(
    incoming: telegram.TelegramIncoming,
    project_tag: str | None,
) -> list[str]:
    """Descarga fotos de Telegram, las sube a storage y crea SourceAssets."""
    saved_urls: list[str] = []
    for file_id in incoming.photo_file_ids:
        try:
            raw = await telegram.download_file(file_id)
        except Exception as exc:
            logger.warning("telegram.photo_download_failed", extra={"file_id": file_id, "err": str(exc)})
            continue
        key = storage.new_key(f"source-assets/telegram/{project_tag or 'untagged'}", "jpg")
        url = storage.upload_bytes(raw, key, content_type="image/jpeg")

        width = height = None
        try:
            from PIL import Image
            import io as _io
            img = Image.open(_io.BytesIO(raw))
            width, height = img.size
        except Exception:
            pass

        await create_source_asset(
            url=url,
            kind="image",
            source_channel="telegram",
            project_tag=project_tag,
            caption=incoming.text or None,
            uploaded_by_wa_id=f"tg:{incoming.chat_id}",
            width=width,
            height=height,
            metadata={"telegram_file_id": file_id, "chat_id": incoming.chat_id},
        )
        saved_urls.append(url)
    return saved_urls


async def _handle_telegram(body: dict) -> None:
    if not settings.telegram_bot_token:
        logger.warning("telegram.token_not_configured")
        return

    incoming = telegram.parse_update(body)
    if incoming is None:
        return  # update sin mensaje (callback_query, etc.)

    logger.info(
        "telegram.incoming",
        extra={
            "chat_id": incoming.chat_id,
            "text": incoming.text[:120],
            "photos": len(incoming.photo_file_ids),
        },
    )

    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(slug=settings.tenant_id, name="Gardens Wood")
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
        tenant_id = tenant.id

    user_id = f"tg:{incoming.chat_id}"
    convo = await _ensure_conversation(tenant_id, user_id, channel="telegram")
    await _log_message(
        convo.id,
        "user",
        incoming.text or f"[{len(incoming.photo_file_ids)} foto(s)]",
    )

    # --- Fotos: ingestar y confirmar ---
    if incoming.photo_file_ids:
        project_tag = _extract_project_tag(incoming.text)
        saved = await _ingest_tg_photos(incoming, project_tag)
        if saved:
            tag_str = f"#{project_tag}" if project_tag else "(sin tag)"
            msg = (
                f"Recibí {len(saved)} foto(s) para el proyecto {tag_str}. "
                "Las podés ver en la biblioteca del dashboard."
            )
            if not project_tag:
                msg += (
                    "\n\nPara agrupar este set como proyecto, respondé con un "
                    "hashtag, ej: #cerco-mendiolaza"
                )
            else:
                msg += (
                    f"\n\nCuando tengas todo el set listo, decime: "
                    f"*generá carrusel {project_tag}* y te armo la pieza."
                )
            try:
                await telegram.send_text(incoming.chat_id, msg)
                await _log_message(convo.id, "assistant", msg, agent="photo_ingester")
            except Exception as exc:
                logger.warning("telegram.reply_failed", exc_info=exc)
        return

    # --- Texto: flujo normal con el graph ---
    if not incoming.text:
        return

    try:
        result = await run_graph(incoming.text, user_id, channel="telegram")
    except Exception as exc:
        logger.exception("graph.failed")
        try:
            await telegram.send_text(
                incoming.chat_id,
                f"Uy, se me cruzaron los cables. Probá de nuevo. ({type(exc).__name__})",
            )
        except Exception:
            pass
        return

    reply = result.get("reply_text", "Listo.")
    await _log_message(convo.id, "assistant", reply, agent="director")
    try:
        await telegram.send_text(incoming.chat_id, reply)
    except Exception as exc:
        logger.warning("telegram.reply_failed", exc_info=exc)


@router.post("/telegram", response_class=Response)
async def telegram_webhook(request: Request, bg: BackgroundTasks):
    """Webhook de Telegram. Registrar con: POST /webhook/telegram/setup."""
    body = await request.json()
    bg.add_task(_handle_telegram, body)
    return Response(status_code=200)


@router.post("/telegram/setup")
async def telegram_setup_webhook(request: Request):
    """Registra el webhook con Telegram. Llamar una sola vez al hacer deploy.

    Body JSON opcional: {"url": "https://tu-dominio.com"}
    Si no se envía URL, usa TELEGRAM_WEBHOOK_URL del env.
    """
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN no configurado")

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    base = body.get("url") or settings.telegram_webhook_url
    if not base:
        raise HTTPException(
            status_code=422,
            detail="Enviá {\"url\": \"https://tu-dominio.com\"} o configurá TELEGRAM_WEBHOOK_URL",
        )
    webhook_url = base.rstrip("/") + "/webhook/telegram"
    result = await telegram.set_webhook(webhook_url)
    return {"ok": True, "webhook_url": webhook_url, "telegram_response": result}
