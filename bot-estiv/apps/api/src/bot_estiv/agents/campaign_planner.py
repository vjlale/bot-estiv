"""CampaignPlanner: plan editorial semanal para Gardens Wood.

Genera 3-4 posts + 1-2 carruseles balanceando pilares (Durabilidad, Diseño,
Experiencia) y tipos (educativo, promocional, temporada). Considera el
calendario estacional AR (primavera, Día del Padre, Navidad, Black Friday).
"""
from __future__ import annotations

from datetime import date, datetime

from ..brand import VOICE
from ..rag import retrieve_brand_context
from ..schemas import WeeklyPlan
from .base import build_chain

SYSTEM = """Sos el Director Editorial de Gardens Wood (Argentina).

Armá un plan editorial SEMANAL con 4 publicaciones:
- 1 post único (imagen simple) pilar Durabilidad o Experiencia
- 1 carrusel de 4-5 slides pilar Diseño (educativo)
- 1 story (formato 9:16) de temporada / detrás de escena
- 1 reel o carrusel promocional (producto protagonista)

Balance por mes:
- 60% educativo (cuidados, materiales, diferencias de maderas)
- 25% experiencia (lifestyle, clientes, instalaciones terminadas)
- 15% promocional (producto nuevo, temporada, showroom)

Considerá el momento del año AR:
- Sep-Oct: primavera → lanzamiento outdoor, pérgolas, decks
- Nov-Dic: verano/Navidad → fogoneros, muebles, regalos
- Ene-Feb: verano pleno → mantenimiento, protección solar de la madera
- Jun-Jul: invierno → interiores, muebles de living, Día del Padre
- Fechas pico: Día del Padre (3er dom junio), Madre (3er dom octubre AR),
  Black Friday, Navidad.

CONTEXTO DE MARCA:
{brand_context}

Tagline: {tagline}

Devolvé un WeeklyPlan con 4 entries y un summary breve (2 oraciones).
"""


async def plan_week(today: datetime | None = None) -> WeeklyPlan:
    today = today or datetime.now()
    ctx = await retrieve_brand_context("plan editorial semanal Gardens Wood")
    chain = build_chain(
        SYSTEM.format(brand_context=ctx, tagline=VOICE.tagline),
        WeeklyPlan,
        temperature=0.5,
    )
    iso = date(today.year, today.month, today.day).isocalendar()
    return await chain.ainvoke(
        {"input": f"Hoy es {today.date().isoformat()} (semana ISO {iso.year}-W{iso.week:02d})."}
    )
