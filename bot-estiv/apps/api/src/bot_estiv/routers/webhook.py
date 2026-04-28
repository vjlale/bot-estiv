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
from ..tools import photo_editor, storage, whatsapp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


TWIML_OK = Response(
    content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    media_type="application/xml",
)


async def _ensure_conversation(tenant_id, wa_id: str) -> Conversation:
    async with AsyncSessionLocal() as session:
        convo = (
            await session.execute(
                select(Conversation).where(Conversation.user_wa_id == wa_id)
            )
        ).scalar_one_or_none()
        if convo is None:
            convo = Conversation(
                tenant_id=tenant_id,
                user_wa_id=wa_id,
                thread_id=f"wa:{wa_id}",
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


def _is_photo_edit_request(text: str) -> bool:
    normalized = (text or "").lower()
    triggers = (
        "edit",
        "editar",
        "editala",
        "editame",
        "proces",
        "lista para subir",
        "dejala lista",
        "post",
        "publicar",
        "mejor",
    )
    return any(trigger in normalized for trigger in triggers)


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


async def _edit_first_photo(incoming) -> str | None:
    if not incoming.media_urls:
        return None

    raw = await whatsapp.download_media(incoming.media_urls[0])
    edited = photo_editor.process_photo(raw, fmt_key="ig_feed_portrait")
    key = storage.new_key("edited/whatsapp", "png")
    return storage.upload_bytes(edited, key, content_type="image/png")


def _signature_urls(request: Request) -> list[str]:
    urls = [str(request.url)]

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if forwarded_proto and forwarded_host:
        urls.append(f"{forwarded_proto}://{forwarded_host}{request.url.path}")

    public_api = settings.next_public_api_base_url.rstrip("/")
    if public_api:
        urls.append(f"{public_api}{request.url.path}")

    return list(dict.fromkeys(urls))


async def _handle(form: dict, signature_urls: list[str], signature: str | None) -> None:
    if settings.app_env != "development":
        valid_signature = bool(
            signature
            and any(
                whatsapp.validate_twilio_signature(url, form, signature)
                for url in signature_urls
            )
        )
        if not valid_signature:
            logger.warning("twilio.signature_invalid", extra={"urls": signature_urls})
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

    convo = await _ensure_conversation(tenant_id, incoming.from_wa)
    await _log_message(convo.id, "user", incoming.body or f"[{incoming.num_media} media]")

    # --- Si vinieron fotos: ingesta + confirmación, sin llamar al graph ---
    if incoming.num_media > 0:
        project_tag = _extract_project_tag(incoming.body)
        saved = await _ingest_photos(incoming, project_tag)
        if _is_photo_edit_request(incoming.body):
            try:
                edited_url = await _edit_first_photo(incoming)
            except Exception as exc:  # noqa: BLE001
                logger.exception("photo_edit.failed")
                msg = f"Recibí la foto, pero falló la edición ({type(exc).__name__})."
                whatsapp.send_text(incoming.from_wa, msg)
                await _log_message(convo.id, "assistant", msg, agent="photo_editor")
                return

            if edited_url and edited_url.startswith("http"):
                msg = (
                    "Listo, te dejé la foto con look Gardens Wood en formato vertical "
                    "para Instagram. Podés descargarla y subirla manualmente."
                )
                whatsapp.send_media(incoming.from_wa, msg, [edited_url])
                await _log_message(convo.id, "assistant", f"{msg}\n{edited_url}", agent="photo_editor")
            else:
                msg = (
                    "Procesé la foto, pero no tengo una URL pública para enviarla por WhatsApp. "
                    "Revisala en el dashboard."
                )
                whatsapp.send_text(incoming.from_wa, msg)
                await _log_message(convo.id, "assistant", msg, agent="photo_editor")
            return

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
        result = await run_graph(incoming.body, incoming.from_wa)
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
    signature_urls = _signature_urls(request)

    if not form.get("From"):
        raise HTTPException(status_code=400, detail="Mensaje inválido")

    bg.add_task(_handle, form, signature_urls, x_twilio_signature)
    return TWIML_OK
