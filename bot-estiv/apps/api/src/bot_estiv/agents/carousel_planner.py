"""CarouselPlanner: dado un topic, produce N SlideBrief con ángulos visuales distintos.

Cada slide tiene:
- headline corto (overlay textual en la imagen)
- body opcional (subtítulo)
- visual_prompt fotográfico concreto (qué encuadrar, cómo, con qué luz)

Los ángulos se eligen para contar una historia progresiva: apertura → detalle →
lifestyle → valor técnico → cierre con CTA visual.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..brand import CATALOG
from ..rag import retrieve_brand_context
from ..schemas import SlideBrief
from .base import build_chain


class CarouselPlan(BaseModel):
    slides: list[SlideBrief] = Field(description="Lista ordenada de slides del carrusel.")


SYSTEM = """Sos el director de arte de Gardens Wood. Planificás carruseles de
Instagram/Facebook con una narrativa visual progresiva y cinematográfica.

ESTRUCTURA RECOMENDADA (adaptá según topic):
  Slide 1 — APERTURA: foto hero amplia que muestre el producto/espacio completo.
  Slide 2 — DETALLE: close-up al material/veta/uniones; revela la artesanía.
  Slide 3 — LIFESTYLE: el espacio habitado, luz cálida, presencia humana sutil.
  Slide 4 — VALOR: foco técnico (durabilidad, proceso, juntas, terminación).
  Slide 5 — CIERRE: plano más amplio de cierre con aire para CTA/logo.

REGLAS VISUALES (OBLIGATORIAS para cada slide):
- Fotografía editorial, nunca render 3D obvio.
- Quebracho argentino, luz natural golden-hour, paleta de marca
  (gris carbón, blanco hueso, quebracho, verde eucalipto, naranja fuego como acento).
- Enfoque selectivo, grano de madera visible, elegancia contenida.
- "Leave clean negative space at the bottom for a typographic overlay; do NOT render text inside the image."
- Cada slide debe diferenciarse visualmente de las anteriores (distinto encuadre, escala o ángulo).

CATÁLOGO DE PRODUCTOS (ÚNICOS permitidos en las imágenes):
{catalog_products}
Materiales: {catalog_materials}

PROHIBIDO depictar (no fabricamos esto):
{catalog_forbidden}

Si el topic sugiere algo fuera del catálogo, reformular el ángulo visual para
usar productos reales que cumplan función similar.

REGLAS DE HEADLINE:
- 4 a 9 palabras, tono sereno, en español rioplatense.
- Nunca uses superlativos ni signos de exclamación.
- El último slide cierra con invitación sutil.

CONTEXTO DE MARCA:
{brand_context}

Tu tarea: producir un CarouselPlan con {n_slides} SlideBrief
(index 1..{n_slides}), manteniendo coherencia narrativa entre ellas.
"""


async def run(topic: str, n_slides: int = 4) -> list[SlideBrief]:
    ctx = await retrieve_brand_context(topic)
    chain = build_chain(
        SYSTEM.format(
            brand_context=ctx,
            n_slides=n_slides,
            catalog_products=", ".join(CATALOG.products),
            catalog_materials=", ".join(CATALOG.materials),
            catalog_forbidden=", ".join(CATALOG.forbidden_in_prompts),
        ),
        CarouselPlan,
        temperature=0.6,
    )
    plan = await chain.ainvoke({"input": f"Topic del carrusel: {topic}"})
    return plan.slides
