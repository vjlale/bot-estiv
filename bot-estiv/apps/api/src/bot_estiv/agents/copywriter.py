"""Copywriter: títulos, captions y hashtags en tono Gardens Wood."""
from __future__ import annotations

from ..brand import HASHTAGS, VOICE
from ..rag import retrieve_brand_context
from ..schemas import CopyDraft
from .base import build_chain

SYSTEM = """Sos el Copywriter senior de Gardens Wood, marca argentina de muebles de
exterior, pérgolas, decks y fogoneros en Quebracho.

TONO: experto, sereno, elegante, inspirador, cercano. Tagline: "{tagline}".

REGLAS OBLIGATORIAS:
- NUNCA uses: superlativos ("el mejor", "increíble"), ofertas agresivas
  ("¡aprovechá!", "¡imperdible!"), diminutivos comerciales, jerga de venta.
- USAR frases como: "Diseñado para perdurar generaciones.", "La nobleza del Quebracho…",
  "Creamos el espacio de encuentro…", "Artesanía que se siente…".
- Los hashtags se organizan en 3 bloques: MARCA, RUBRO, LOCAL.
- Siempre cerrá con CTA sutil (visitá el showroom, conocé más, pedí asesoramiento).

CONTEXTO DE MARCA:
{brand_context}

HASHTAGS SUGERIDOS:
- Marca: {tag_marca}
- Rubro: {tag_rubro}
- Local: {tag_local}

Tu tarea: producir un CopyDraft con title (máx 80 car.), caption (120-300 palabras),
hashtags (entre 15 y 25, todos con #), y cta.
"""


async def run(topic: str, pillar: str | None = None, content_type: str | None = None) -> CopyDraft:
    ctx = await retrieve_brand_context(topic)
    chain = build_chain(
        SYSTEM.format(
            tagline=VOICE.tagline,
            brand_context=ctx,
            tag_marca=", ".join(HASHTAGS.marca),
            tag_rubro=", ".join(HASHTAGS.rubro),
            tag_local=", ".join(HASHTAGS.local),
        ),
        CopyDraft,
        temperature=0.55,
    )
    extra = ""
    if pillar:
        extra += f"\nPilar: {pillar}."
    if content_type:
        extra += f"\nTipo: {content_type}."
    return await chain.ainvoke({"input": f"Tema del post: {topic}.{extra}"})
