"""TrendScout: calendario estacional AR + tendencias de jardinería/paisajismo."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from ..rag import retrieve_brand_context
from .base import build_chain


class TrendIdea(BaseModel):
    title: str
    pillar: str
    content_type: str
    why_now: str
    hashtags: list[str]


class TrendReport(BaseModel):
    month: str
    ideas: list[TrendIdea] = Field(default_factory=list)
    seasonal_events: list[str] = Field(default_factory=list)


SYSTEM = """Sos el Trend Scout de Gardens Wood.

Tu rol: detectar tendencias y fechas clave del rubro madereras + jardinería +
paisajismo + muebles de exterior en Argentina, y proponer ideas de contenido.

Considerá:
- Calendario AR: estaciones, Día del Padre/Madre (AR), Black Friday,
  Navidad, vacaciones, Día del Jardín (1 de sept Argentina).
- Búsquedas típicas del segmento: "pérgolas", "quinchos modernos",
  "decks de quebracho", "fogoneros", "muebles de galería".
- Temporadas: en primavera suben búsquedas outdoor; invierno, interiores.

CONTEXTO DE MARCA:
{brand_context}

Devolvé un TrendReport con 6-8 ideas para el mes actual, con why_now claro."""


async def scout(today: date | None = None) -> TrendReport:
    today = today or date.today()
    ctx = await retrieve_brand_context("tendencias jardinería paisajismo AR")
    chain = build_chain(
        SYSTEM.format(brand_context=ctx),
        TrendReport,
        temperature=0.6,
    )
    return await chain.ainvoke({"input": f"Mes actual: {today.strftime('%B %Y')}."})
