"""AnalyticsAgent: KPIs de IG/FB + Ads con recomendaciones accionables."""
from __future__ import annotations

import logging

from ..rag import retrieve_brand_context
from ..schemas import AnalyticsReport
from ..tools import meta_ads, meta_graph
from .base import build_chain

logger = logging.getLogger(__name__)


SYSTEM = """Sos el Head of Analytics de Gardens Wood.

Analizás performance de IG/FB orgánico + Meta Ads y devolvés un reporte
con KPIs (alcance, engagement, CPA, ROAS), top posts, y 3-6 recomendaciones
concretas (qué formato priorizar, qué horarios, qué pilares de marca
están sub-representados).

Reglas:
- Todo número viene con comparación vs período anterior cuando sea posible.
- Recomendaciones 100% accionables (ej: "Publicar más carruseles educativos los
  martes 19hs: el pilar Diseño tiene +42% engagement").
- Nunca recomendar tono agresivo de venta.

CONTEXTO DE MARCA:
{brand_context}

DATOS:
- IG cuenta insights: {ig_account}
- Ads (campañas - últimos 7 días): {ads_summary}
"""


async def weekly_report() -> AnalyticsReport:
    ctx = await retrieve_brand_context("métricas y analítica Gardens Wood")
    try:
        ig = await meta_graph.ig_insights()
    except Exception:
        ig = {"error": "no disponible"}
    try:
        ads = meta_ads.account_insights(date_preset="last_7_d")
    except Exception:
        ads = []

    chain = build_chain(
        SYSTEM.format(brand_context=ctx, ig_account=ig, ads_summary=ads[:10]),
        AnalyticsReport,
        temperature=0.3,
    )
    return await chain.ainvoke(
        {"input": "Generá el reporte semanal con recomendaciones para las próximas 2 semanas."}
    )
