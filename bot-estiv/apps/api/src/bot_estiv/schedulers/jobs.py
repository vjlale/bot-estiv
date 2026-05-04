"""Jobs que corren en el worker ARQ.

- weekly_plan_reminder: lunes 09:00 → envía plan semanal por WhatsApp
- pre_publish_reminder: 24h antes → reminder con preview
- publish_scheduled: cada 5 min → publica lo que venció en IG/FB
- refresh_analytics_snapshot: diario 02:00 → guarda snapshot
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

from ..agents import campaign_planner
from ..config import settings
from ..db import AsyncSessionLocal
from ..models import AnalyticsSnapshot, Post, PostStatus, Tenant
from ..tools import meta_graph, whatsapp

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    return datetime.utcnow()


async def _default_tenant_id() -> uuid.UUID:
    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
        ).scalar_one_or_none()
        if row:
            return row.id
        tenant = Tenant(slug=settings.tenant_id, name="Gardens Wood")
        s.add(tenant)
        await s.commit()
        await s.refresh(tenant)
        return tenant.id


async def weekly_plan_reminder(ctx) -> dict:
    plan = await campaign_planner.plan_week()
    entries = "\n".join(
        f"- {e.day} {e.slot}: {e.format} | {e.pillar} → {e.topic}" for e in plan.entries
    )
    body = (
        f"*Bot Estiv — Plan editorial semana {plan.week_of}*\n\n"
        f"{entries}\n\n{plan.summary}\n\n"
        "Respondé: _generá los posts de esta semana_ para arrancar."
    )
    whatsapp.send_text(settings.twilio_whatsapp_to, body)
    return {"entries": len(plan.entries)}


async def pre_publish_reminder(ctx) -> dict:
    """Busca posts scheduled en las próximas 24h y manda recordatorio."""
    now = _utcnow_naive()
    window_end = now + timedelta(hours=24)
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                select(Post).where(
                    Post.status == PostStatus.SCHEDULED,
                    Post.scheduled_for.isnot(None),
                    Post.scheduled_for <= window_end,
                    Post.scheduled_for > now,
                )
            )
        ).scalars().all()

    if not rows:
        return {"reminded": 0}
    body = "*Próximas publicaciones (24h):*\n" + "\n".join(
        f"- {p.scheduled_for.isoformat()} — {p.title}" for p in rows
    )
    whatsapp.send_text(settings.twilio_whatsapp_to, body)
    return {"reminded": len(rows)}


async def publish_scheduled(ctx) -> dict:
    """Publica posts cuya scheduled_for ya venció."""
    now = _utcnow_naive()
    published = 0
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                select(Post).where(
                    Post.status == PostStatus.SCHEDULED,
                    Post.scheduled_for.isnot(None),
                    Post.scheduled_for <= now,
                )
            )
        ).scalars().all()
        published_titles: list[str] = []
        failed_titles: list[str] = []
        for p in rows:
            try:
                urls = [a.url for a in await _post_assets(s, p.id)]
                caption = f"{p.title}\n\n{p.caption}\n\n" + " ".join(p.hashtags or [])
                if len(urls) > 1:
                    meta_id = await meta_graph.ig_publish_carousel(urls, caption)
                elif p.format == "ig_story":
                    meta_id = await meta_graph.ig_publish_story(urls[0])
                else:
                    meta_id = await meta_graph.ig_publish_image(urls[0], caption)
                p.status = PostStatus.PUBLISHED
                p.published_at = now
                p.meta_post_id = meta_id
                published += 1
                published_titles.append(p.title)
            except Exception as exc:
                logger.exception("publish_failed")
                p.status = PostStatus.FAILED
                p.brand_check = {"publish_error": str(exc)}
                failed_titles.append(f"{p.title} ({exc})")
        await s.commit()

    if published_titles and settings.twilio_whatsapp_to:
        try:
            whatsapp.send_text(
                settings.twilio_whatsapp_to,
                "✅ *Posts publicados en Instagram:*\n" + "\n".join(f"• {t}" for t in published_titles),
            )
        except Exception as exc:
            logger.warning("notify.publish_ok_failed", exc_info=exc)

    if failed_titles and settings.twilio_whatsapp_to:
        try:
            whatsapp.send_text(
                settings.twilio_whatsapp_to,
                "⚠️ *Publicación fallida — revisá el dashboard:*\n"
                + "\n".join(f"• {t}" for t in failed_titles),
            )
        except Exception as exc:
            logger.warning("notify.publish_fail_failed", exc_info=exc)

    return {"published": published}


async def _post_assets(session, post_id):
    from ..models import Asset

    return (
        await session.execute(
            select(Asset).where(Asset.post_id == post_id).order_by(Asset.slide_index.asc())
        )
    ).scalars().all()


async def refresh_analytics_snapshot(ctx) -> dict:
    now = _utcnow_naive()
    try:
        data = await meta_graph.ig_insights()
    except Exception as exc:
        logger.warning("analytics.ig_failed", exc_info=exc)
        data = {"error": str(exc)}
    tenant_id = await _default_tenant_id()
    async with AsyncSessionLocal() as s:
        s.add(
            AnalyticsSnapshot(
                tenant_id=tenant_id,
                source="ig",
                period_start=now - timedelta(days=1),
                period_end=now,
                data=data if isinstance(data, dict) else {"raw": str(data)},
            )
        )
        await s.commit()
    return {"ok": True}
