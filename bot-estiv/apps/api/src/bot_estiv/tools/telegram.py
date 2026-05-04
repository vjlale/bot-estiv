"""Integración con Telegram Bot API via webhooks.

Espeja el patrón de whatsapp.py: parse_update, send_text, send_photo,
send_approval_request, download_file.

Configuración requerida:
    TELEGRAM_BOT_TOKEN=<token>
    TELEGRAM_WEBHOOK_URL=https://tu-dominio.com   (para registrar el webhook)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

_TG_BASE = "https://api.telegram.org"


def _api_url(method: str) -> str:
    return f"{_TG_BASE}/bot{settings.telegram_bot_token}/{method}"


# ---------- Estructuras ----------

@dataclass
class TelegramIncoming:
    chat_id: int
    user_id: int
    text: str
    photo_file_ids: list[str] = field(default_factory=list)
    message_id: int = 0
    username: str | None = None
    raw: dict[str, Any] | None = None


def parse_update(body: dict) -> TelegramIncoming | None:
    """Parsea un Update de Telegram. Devuelve None si no es mensaje procesable."""
    msg = body.get("message") or body.get("edited_message")
    if not msg:
        return None
    chat = msg.get("chat", {})
    sender = msg.get("from", {})
    text = (msg.get("text") or msg.get("caption") or "").strip()
    photo_file_ids: list[str] = []
    if "photo" in msg:
        # Telegram envía lista ordenada de menor a mayor resolución; el último es el mejor
        photo_file_ids = [msg["photo"][-1]["file_id"]]
    return TelegramIncoming(
        chat_id=chat["id"],
        user_id=sender.get("id", chat["id"]),
        text=text,
        photo_file_ids=photo_file_ids,
        message_id=msg.get("message_id", 0),
        username=sender.get("username"),
        raw=msg,
    )


# ---------- API helpers ----------

async def _post(method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(_api_url(method), json=payload)
        resp.raise_for_status()
        return resp.json()


async def send_text(chat_id: int | str, text: str) -> dict:
    """Envía un mensaje de texto (Markdown V1)."""
    result = await _post("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    })
    logger.info("telegram.sent", extra={"chat_id": chat_id, "chars": len(text)})
    return result


async def send_photo(
    chat_id: int | str,
    photo_url: str,
    caption: str = "",
) -> dict:
    """Envía una foto por URL pública."""
    return await _post("sendPhoto", {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown",
    })


async def send_video(
    chat_id: int | str,
    video_url: str,
    caption: str = "",
) -> dict:
    """Envía un video por URL pública (MP4)."""
    return await _post("sendVideo", {
        "chat_id": chat_id,
        "video": video_url,
        "caption": caption,
        "parse_mode": "Markdown",
        "supports_streaming": True,
    })


async def send_approval_request(
    chat_id: int | str,
    preview_urls: list[str],
    caption: str,
    post_id: str,
) -> None:
    """Envía preview de post + instrucciones de aprobación por Telegram."""
    for i, url in enumerate(preview_urls):
        cap = caption if i == 0 else f"[{i + 1}/{len(preview_urls)}]"
        try:
            await send_photo(chat_id, url, cap)
        except Exception as exc:
            logger.warning(
                "telegram.send_photo_failed",
                extra={"url": url, "err": str(exc)},
            )
    footer = (
        f"— Preview listo para revisar —\n"
        f"Respondé:\n"
        f"  *APROBAR* {post_id}\n"
        f"  *EDITAR* {post_id} <tu feedback>\n"
        f"  *CANCELAR* {post_id}"
    )
    await send_text(chat_id, footer)


async def get_file_url(file_id: str) -> str:
    """Devuelve la URL de descarga de un archivo de Telegram."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_api_url("getFile"), params={"file_id": file_id})
        resp.raise_for_status()
        data = resp.json()
    file_path = data["result"]["file_path"]
    return f"{_TG_BASE}/file/bot{settings.telegram_bot_token}/{file_path}"


async def download_file(file_id: str) -> bytes:
    """Descarga el contenido de un archivo de Telegram."""
    url = await get_file_url(file_id)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def set_webhook(webhook_url: str) -> dict:
    """Registra la URL del webhook con Telegram (llamar una vez al hacer deploy)."""
    result = await _post("setWebhook", {
        "url": webhook_url,
        "drop_pending_updates": True,
        "allowed_updates": ["message", "edited_message"],
    })
    logger.info("telegram.webhook_set", extra={"url": webhook_url, "result": result})
    return result


async def delete_webhook() -> dict:
    """Elimina el webhook (para volver a polling en desarrollo)."""
    return await _post("deleteWebhook", {"drop_pending_updates": False})
