"""Generación de imágenes con Gemini 3.1 Flash Image (Nano Banana 2).

Único proveedor del stack. Soporta:
- Generación pura desde prompt
- Edición / variaciones a partir de imágenes de referencia (incluido logo de marca)

El recorte/resize al formato exacto (feed, story, carrusel) lo hace
`canvas_design.fit_to_format` después.
"""
from __future__ import annotations

import logging
from typing import Iterable

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def generate(
    prompt: str,
    width: int | None = None,
    height: int | None = None,
    reference_images: Iterable[bytes] | None = None,
) -> bytes:
    """Genera o edita una imagen con Nano Banana 2 y devuelve los bytes (PNG/JPEG).

    `width` y `height` se mantienen por compatibilidad pero hoy Gemini decide
    el tamaño internamente; el ajuste final lo hace canvas_design.fit_to_format.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.google_api_key)
    parts: list = []

    enriched_prompt = prompt
    if width and height:
        enriched_prompt = (
            f"{prompt}\n\nFormat hint: aspect ratio {width}x{height} px."
        )
    parts.append(enriched_prompt)

    for img in reference_images or []:
        parts.append(types.Part.from_bytes(data=img, mime_type="image/png"))

    response = client.models.generate_content(
        model=settings.gemini_image_model,
        contents=parts,
    )
    for part in response.candidates[0].content.parts:
        inline = getattr(part, "inline_data", None)
        if inline and inline.data:
            return inline.data
    raise RuntimeError("Gemini Nano Banana no devolvió datos de imagen")


# Alias por compatibilidad con código antiguo que importaba estas funciones
generate_with_gemini = generate


async def download_image(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content
