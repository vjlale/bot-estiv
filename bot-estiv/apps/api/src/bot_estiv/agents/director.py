"""Bot Estiv — Director / Supervisor LangGraph.

Clasifica la intención del usuario y orquesta los agentes especialistas.
Soporta 6 intents principales:
  1. create_post            → Copywriter + ContentDesigner + BrandGuardian + Approval
  2. edit_video_story       → VideoEditor (requiere media de entrada)
  3. weekly_plan            → CampaignPlanner
  4. ads_change             → MetaAdsManager
  5. analytics_report       → AnalyticsAgent
  6. trend_ideas            → TrendScout
  7. chitchat / help        → respuesta conversacional

Usa handoff pattern de LangGraph (routing por intent).
"""
from __future__ import annotations

import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..llm import get_chat_model

logger = logging.getLogger(__name__)


Intent = Literal[
    "create_post",
    "edit_video_story",
    "weekly_plan",
    "ads_change",
    "analytics_report",
    "trend_ideas",
    "approval_decision",
    "chitchat",
]


class RoutingDecision(BaseModel):
    intent: Intent
    topic: str = Field(default="", description="Tema/brief extraído del mensaje")
    format: str | None = None
    pillar: str | None = None
    content_type: str | None = None
    slides: int | None = None
    post_id: str | None = None
    decision: str | None = None
    reason: str | None = None


SYSTEM = """Sos *Bot Estiv*, el Director de Marketing Digital de Gardens Wood
(muebles y estructuras de exterior en Quebracho argentino).

Tu tarea es clasificar cada mensaje entrante y extraer parámetros clave en JSON.

Intents válidos:
- create_post: pide crear un post / carrusel / story / reel. Extraé topic, format, pillar,
  content_type y slides si lo menciona.
- edit_video_story: pide agregar texto o diseño a un video.
- weekly_plan: pide plan editorial semanal o recordatorio.
- ads_change: crear/modificar/pausar campañas Meta Ads.
- analytics_report: pide métricas o análisis de performance.
- trend_ideas: pide ideas, tendencias o temporadas.
- approval_decision: mensaje comienza con APROBAR / EDITAR / CANCELAR + UUID.
- chitchat: saludo o pregunta genérica.

Formatos válidos: ig_feed_portrait, ig_feed_square, ig_story, ig_reel, fb_feed,
carousel_portrait, carousel_square, video_story.
Pilares: durabilidad, diseno, experiencia.
Content_type: educativo, promocional, temporada.
"""


def classify(user_message: str) -> RoutingDecision:
    """Clasificador rápido: primero regex para aprobaciones, luego LLM estructurado."""
    text = user_message.strip()
    upper = text.upper()
    for keyword in ("APROBAR", "EDITAR", "CANCELAR"):
        if upper.startswith(keyword):
            parts = text.split(maxsplit=2)
            post_id = parts[1] if len(parts) > 1 else None
            reason = parts[2] if len(parts) > 2 else None
            return RoutingDecision(
                intent="approval_decision",
                decision=keyword.lower(),
                post_id=post_id,
                reason=reason,
                topic="",
            )

    llm = get_chat_model(temperature=0.0).with_structured_output(RoutingDecision)
    result = llm.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(content=text),
        ]
    )
    return result  # type: ignore[return-value]
