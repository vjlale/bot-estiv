"""LangGraph supervisor de Bot Estiv.

Estado del grafo:
- messages: historial
- intent: resultado del Director
- draft_copy, brief, preview_urls, post_id, report: artefactos por agente

Nodos:
- router → director.classify
- copywriter → genera copy
- designer → genera imágenes
- brand_guardian → valida
- save_post → persiste Post + Assets en DB
- approval → envía preview por WhatsApp y marca post pending_approval
- planner → WeeklyPlan
- ads → MetaAdsManager
- analytics → AnalyticsAgent
- trends → TrendScout
- approval_decision → actualiza Approval + ejecuta publicación
- reply → responde por WhatsApp si hace falta
"""
from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy import select
from typing_extensions import TypedDict

from .agents import (
    analytics as analytics_agent,
)
from .agents import (
    brand_guardian,
    campaign_planner,
    content_designer,
    copywriter,
    director,
    meta_ads_manager,
    trend_scout,
    video_editor,
)
from .config import settings
from .db import AsyncSessionLocal
from .models import (
    Approval,
    Asset,
    Post,
    PostFormat,
    PostStatus,
    Tenant,
)
from .schemas import DesignBrief, SlideBrief
from .tools import whatsapp

logger = logging.getLogger(__name__)


class State(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_wa_id: str      # identificador único: "whatsapp:+54..." o "tg:12345678"
    channel: str         # "whatsapp" | "telegram"
    user_text: str
    media_bytes: bytes   # video/foto cruda enviada por el usuario (para edit_video_story)
    routing: dict[str, Any]
    draft_copy: dict[str, Any]
    brief: dict[str, Any]
    preview_urls: list[str]
    post_id: str
    brand_check: dict[str, Any]
    reply_text: str
    ads_plan: dict[str, Any]
    report: dict[str, Any]


# ---------- Utilidades ----------

async def _get_tenant_id() -> uuid.UUID:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
        ).scalar_one_or_none()
        if row is None:
            tenant = Tenant(
                slug=settings.tenant_id,
                name=settings.tenant_id.replace("-", " ").title(),
            )
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            return tenant.id
        return row.id


# ---------- Nodes ----------

async def node_router(state: State) -> State:
    decision = director.classify(state["user_text"])
    state["routing"] = decision.model_dump()
    logger.info("director.route", extra={"intent": decision.intent})
    return state


async def node_copywriter(state: State) -> State:
    r = state["routing"]
    draft = await copywriter.run(
        topic=r.get("topic") or "",
        pillar=r.get("pillar"),
        content_type=r.get("content_type"),
    )
    state["draft_copy"] = draft.model_dump()
    return state


async def node_designer(state: State) -> State:
    r = state["routing"]
    copy = state["draft_copy"]
    slides_n = r.get("slides") or 0
    fmt = r.get("format") or "ig_feed_portrait"

    slides: list[SlideBrief] = []
    if slides_n and slides_n > 1:
        title = copy.get("title", "")
        caption = copy.get("caption", "")
        chunks = [caption[i : i + 200] for i in range(0, len(caption), 200)][:slides_n]
        for i, body in enumerate(chunks):
            slides.append(
                SlideBrief(
                    index=i,
                    headline=title if i == 0 else f"{title} — {i + 1}",
                    body=body,
                    visual_prompt=r.get("topic") or title,
                )
            )
        fmt = "carousel_portrait"

    brief = DesignBrief(
        format=fmt,
        pillar=r.get("pillar"),
        content_type=r.get("content_type"),
        topic=r.get("topic") or copy.get("title", ""),
        slides=slides,
    )
    state["brief"] = brief.model_dump()
    urls = await content_designer.generate_post(brief)
    state["preview_urls"] = urls
    return state


async def node_brand_guardian(state: State) -> State:
    copy = state["draft_copy"]
    from .schemas import CopyDraft

    check = brand_guardian.validate_copy(CopyDraft(**copy))
    state["brand_check"] = check.model_dump()
    return state


async def node_save_post(state: State) -> State:
    copy = state["draft_copy"]
    brief = state["brief"]
    urls = state["preview_urls"]
    tenant_id = await _get_tenant_id()

    fmt = brief["format"]
    post_fmt = PostFormat.CAROUSEL if len(urls) > 1 else PostFormat(fmt if fmt in {f.value for f in PostFormat} else "ig_feed_portrait")

    async with AsyncSessionLocal() as session:
        post = Post(
            tenant_id=tenant_id,
            title=copy["title"],
            caption=copy["caption"],
            hashtags=copy.get("hashtags"),
            format=post_fmt,
            status=PostStatus.PENDING_APPROVAL,
            pillar=brief.get("pillar"),
            content_type=brief.get("content_type"),
            brand_check=state.get("brand_check"),
            created_by_agent="director",
        )
        session.add(post)
        await session.flush()
        for i, url in enumerate(urls):
            session.add(
                Asset(
                    post_id=post.id,
                    tenant_id=tenant_id,
                    kind="image",
                    url=url,
                    slide_index=i if len(urls) > 1 else None,
                )
            )
        await session.commit()
        state["post_id"] = str(post.id)
    return state


async def node_approval(state: State) -> State:
    from .tools import telegram as tg_tool

    urls = state["preview_urls"]
    copy = state["draft_copy"]
    caption = (
        f"{copy['title']}\n\n{copy['caption']}\n\n"
        + " ".join(copy.get("hashtags") or [])
    )
    user_id = state["user_wa_id"]
    post_id = state["post_id"]
    channel = state.get("channel", "whatsapp")

    if channel == "telegram":
        chat_id = int(user_id.removeprefix("tg:"))
        try:
            await tg_tool.send_approval_request(chat_id, urls, caption, post_id)
        except Exception as exc:
            logger.warning("telegram.approval_send_failed", exc_info=exc)
    else:
        try:
            whatsapp.send_approval_request(user_id, urls, caption, post_id)
        except Exception as exc:
            logger.warning("whatsapp.send_failed", exc_info=exc)

    async with AsyncSessionLocal() as session:
        session.add(
            Approval(
                post_id=uuid.UUID(post_id),
                requested_to_wa_id=user_id,
                status="pending",
            )
        )
        await session.commit()
    state["reply_text"] = f"Preview enviado. Respondé APROBAR/EDITAR/CANCELAR {post_id}."
    return state


async def node_planner(state: State) -> State:
    plan = await campaign_planner.plan_week()
    state["report"] = plan.model_dump()
    entries = "\n".join(
        f"- {e.day} {e.slot}: {e.format} | {e.pillar} | {e.content_type} → {e.topic}"
        for e in plan.entries
    )
    state["reply_text"] = (
        f"*Plan editorial — semana del {plan.week_of}*\n\n{entries}\n\n_{plan.summary}_"
    )
    return state


async def node_ads(state: State) -> State:
    plan = await meta_ads_manager.plan_changes(state["user_text"])
    state["ads_plan"] = plan.model_dump()
    actions = "\n".join(
        f"- {a.kind.upper()}: {a.name or a.campaign_id or ''} — {a.reason}" for a in plan.actions
    )
    state["reply_text"] = (
        f"*Propuesta Meta Ads*\n{actions}\n\n_Resumen:_ {plan.summary}\n"
        f"_Impacto esperado:_ {plan.expected_impact}\n\n"
        "Respondé APLICAR para ejecutar o CANCELAR para descartar."
    )
    return state


async def node_analytics(state: State) -> State:
    report = await analytics_agent.weekly_report()
    state["report"] = report.model_dump()
    recs = "\n".join(f"• {r}" for r in report.recommendations)
    state["reply_text"] = (
        f"*Reporte — {report.period}*\nKPIs: {report.kpis}\n\nRecomendaciones:\n{recs}"
    )
    return state


async def node_trends(state: State) -> State:
    report = await trend_scout.scout()
    state["report"] = report.model_dump()
    ideas = "\n".join(f"• [{i.pillar}] {i.title} — {i.why_now}" for i in report.ideas[:6])
    state["reply_text"] = f"*Tendencias — {report.month}*\n{ideas}"
    return state


async def node_approval_decision(state: State) -> State:
    r = state["routing"]
    post_id_s = r.get("post_id")
    decision = r.get("decision")
    reason = r.get("reason")
    if not post_id_s:
        state["reply_text"] = "No pude identificar el ID del post. Incluí el UUID."
        return state
    try:
        post_uuid = uuid.UUID(post_id_s)
    except ValueError:
        state["reply_text"] = f"ID inválido: {post_id_s}"
        return state

    from datetime import datetime

    async with AsyncSessionLocal() as session:
        post = (await session.execute(select(Post).where(Post.id == post_uuid))).scalar_one_or_none()
        if post is None:
            state["reply_text"] = f"No encuentro el post {post_id_s}."
            return state

        approval = (
            await session.execute(
                select(Approval).where(Approval.post_id == post_uuid, Approval.status == "pending")
            )
        ).scalar_one_or_none()

        if decision == "aprobar":
            post.status = PostStatus.APPROVED
            if approval:
                approval.status = "approved"
                approval.decided_at = datetime.utcnow()
            state["reply_text"] = f"Post {post_id_s} aprobado. Se programará para publicación."
        elif decision == "cancelar":
            post.status = PostStatus.REJECTED
            if approval:
                approval.status = "rejected"
                approval.decided_at = datetime.utcnow()
                approval.decision_reason = reason
            state["reply_text"] = f"Post {post_id_s} cancelado."
        elif decision == "editar":
            post.status = PostStatus.DRAFT
            if approval:
                approval.status = "edit_requested"
                approval.decided_at = datetime.utcnow()
                approval.decision_reason = reason
            state["reply_text"] = (
                f"Anotado el feedback. Regenero en breve con: {reason or '(sin detalle)'}."
            )
        await session.commit()
    return state


async def node_edit_video_story(state: State) -> State:
    """Edita un video/foto enviado por el usuario: overlay de texto + logo + formato 9:16."""
    from .tools import telegram as tg_tool

    media = state.get("media_bytes")
    if not media:
        state["reply_text"] = (
            "Mandame el video o foto que querés convertir en historia y "
            "en el mismo mensaje decime el titular (ej: *Pérgola de Quebracho*)."
        )
        return state

    headline = state.get("user_text", "Gardens Wood")
    channel = state.get("channel", "whatsapp")
    user_id = state["user_wa_id"]

    try:
        video_url = await video_editor.edit_story(media, headline)
    except Exception as exc:
        logger.warning("video_editor.failed", exc_info=exc)
        state["reply_text"] = (
            f"No pude procesar el video ({type(exc).__name__}). "
            "Revisá que sea MP4/MOV/JPEG y volvé a intentar."
        )
        return state

    if channel == "telegram":
        chat_id = int(user_id.removeprefix("tg:"))
        try:
            await tg_tool.send_video(chat_id, video_url, "Historia procesada con look Gardens Wood ✓")
        except Exception as exc:
            logger.warning("telegram.send_failed", exc_info=exc)
    else:
        try:
            whatsapp.send_media(
                user_id,
                "Historia procesada con look Gardens Wood. Descargala y subila a IG.",
                [video_url],
            )
        except Exception as exc:
            logger.warning("whatsapp.send_failed", exc_info=exc)

    state["reply_text"] = f"Historia lista: {video_url}"
    return state


async def node_chitchat(state: State) -> State:
    state["reply_text"] = (
        "Hola, soy *Bot Estiv* — tu director de marketing de Gardens Wood.\n"
        "Pedime cosas como:\n"
        "• _Hacé un carrusel educativo de 4 slides sobre cuidados del Quebracho_\n"
        "• _Planificá la semana_\n"
        "• _Cómo viene la campaña de pérgolas_\n"
        "• _Ideas de temporada_\n"
        "• _Mandame un video para convertir en historia de Instagram_\n"
    )
    return state


def _route(state: State) -> str:
    intent = state["routing"]["intent"]
    mapping = {
        "create_post": "copywriter",
        "edit_video_story": "edit_video_story",
        "weekly_plan": "planner",
        "ads_change": "ads",
        "analytics_report": "analytics",
        "trend_ideas": "trends",
        "approval_decision": "approval_decision",
        "chitchat": "chitchat",
    }
    return mapping.get(intent, "chitchat")


def build_graph():
    g: StateGraph = StateGraph(State)
    g.add_node("router", node_router)
    g.add_node("copywriter", node_copywriter)
    g.add_node("designer", node_designer)
    g.add_node("brand_guardian", node_brand_guardian)
    g.add_node("save_post", node_save_post)
    g.add_node("approval", node_approval)
    g.add_node("planner", node_planner)
    g.add_node("ads", node_ads)
    g.add_node("analytics", node_analytics)
    g.add_node("trends", node_trends)
    g.add_node("approval_decision", node_approval_decision)
    g.add_node("edit_video_story", node_edit_video_story)
    g.add_node("chitchat", node_chitchat)

    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router",
        _route,
        {
            "copywriter": "copywriter",
            "planner": "planner",
            "ads": "ads",
            "analytics": "analytics",
            "trends": "trends",
            "approval_decision": "approval_decision",
            "edit_video_story": "edit_video_story",
            "chitchat": "chitchat",
        },
    )
    g.add_edge("copywriter", "designer")
    g.add_edge("designer", "brand_guardian")
    g.add_edge("brand_guardian", "save_post")
    g.add_edge("save_post", "approval")
    g.add_edge("approval", END)
    g.add_edge("planner", END)
    g.add_edge("ads", END)
    g.add_edge("analytics", END)
    g.add_edge("trends", END)
    g.add_edge("approval_decision", END)
    g.add_edge("edit_video_story", END)
    g.add_edge("chitchat", END)
    return g.compile()


GRAPH = build_graph()


async def run_graph(
    user_text: str,
    user_wa_id: str,
    channel: str = "whatsapp",
    media_bytes: bytes | None = None,
) -> State:
    state: State = {
        "user_text": user_text,
        "user_wa_id": user_wa_id,
        "channel": channel,
        "messages": [],
    }
    if media_bytes is not None:
        state["media_bytes"] = media_bytes
    return await GRAPH.ainvoke(state)
