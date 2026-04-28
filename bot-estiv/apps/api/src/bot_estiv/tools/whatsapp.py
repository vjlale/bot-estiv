"""Integración con Twilio WhatsApp Business API.

Twilio WhatsApp soporta:
- Mensajes de texto y media (persistentResistentent URL via HTTPS)
- Botones Quick Reply via Content Templates (ContentSid)
- Webhook de entrada firmado con X-Twilio-Signature

Este módulo encapsula el cliente y provee helpers para enviar
previews de aprobación con tres botones: Aprobar / Editar / Cancelar.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    from_wa: str            # "whatsapp:+54..."
    to_wa: str
    body: str
    num_media: int
    media_urls: list[str]
    message_sid: str
    button_payload: str | None = None  # cuando el usuario toca un Quick Reply
    raw: dict[str, Any] | None = None


def get_client() -> Client:
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, params, signature)


def parse_incoming(form: dict[str, Any]) -> IncomingMessage:
    num_media = int(form.get("NumMedia", 0) or 0)
    media_urls = [form.get(f"MediaUrl{i}", "") for i in range(num_media)]
    return IncomingMessage(
        from_wa=form.get("From", ""),
        to_wa=form.get("To", ""),
        body=(form.get("Body") or "").strip(),
        num_media=num_media,
        media_urls=[u for u in media_urls if u],
        message_sid=form.get("MessageSid", ""),
        button_payload=form.get("ButtonPayload") or form.get("ButtonText"),
        raw=form,
    )


def send_text(to_wa: str, body: str) -> str:
    client = get_client()
    msg = client.messages.create(
        from_=settings.twilio_whatsapp_from,
        to=to_wa,
        body=body,
    )
    logger.info("whatsapp.sent", extra={"sid": msg.sid, "to": to_wa})
    return msg.sid


def send_media(to_wa: str, body: str, media_urls: list[str]) -> list[str]:
    """Envía hasta 10 media URLs en un mismo mensaje (limitación Twilio: 1 por msg).

    Cuando hay carrusel, se envían N mensajes en orden con índice en caption.
    """
    client = get_client()
    sids = []
    for i, url in enumerate(media_urls):
        caption = body if i == 0 else f"[{i + 1}/{len(media_urls)}]"
        msg = client.messages.create(
            from_=settings.twilio_whatsapp_from,
            to=to_wa,
            body=caption,
            media_url=[url],
        )
        sids.append(msg.sid)
    return sids


def send_approval_request(
    to_wa: str,
    preview_urls: list[str],
    caption: str,
    post_id: str,
) -> list[str]:
    """Envía preview + instrucciones de aprobación.

    Como Quick Reply templates requieren pre-aprobación por Meta, en MVP
    usamos texto con instrucciones:
        Respondé: APROBAR {post_id} / EDITAR {post_id} / CANCELAR {post_id}
    """
    sids = send_media(to_wa, caption, preview_urls) if preview_urls else []
    footer = (
        f"\n\n— Preview listo para revisar —\n"
        f"Respondé:\n"
        f"  *APROBAR* {post_id}\n"
        f"  *EDITAR* {post_id} <tu feedback>\n"
        f"  *CANCELAR* {post_id}"
    )
    sids.append(send_text(to_wa, footer))
    return sids


async def download_media(url: str) -> bytes:
    """Descarga media de Twilio (requiere basic auth con SID + token)."""
    async with httpx.AsyncClient(
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content
