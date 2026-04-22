"""Retriever de contexto de marca para los agentes."""
from __future__ import annotations

from sqlalchemy import select

from ..brand import BRAND_SUMMARY
from ..db import AsyncSessionLocal
from ..llm import get_embeddings
from ..models import BrandDocument, Tenant
from ..config import settings


async def retrieve_brand_context(query: str, k: int = 5) -> str:
    """Busca los k chunks más similares al query y los arma como contexto.

    Fallback: si no hay embeddings/rows, devuelve el BRAND_SUMMARY estático.
    """
    try:
        emb = get_embeddings().embed_query(query)
    except Exception:
        return BRAND_SUMMARY

    async with AsyncSessionLocal() as session:
        tenant_row = (
            await session.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
        ).scalar_one_or_none()
        if tenant_row is None:
            return BRAND_SUMMARY

        stmt = (
            select(BrandDocument)
            .where(
                BrandDocument.tenant_id == tenant_row.id,
                BrandDocument.embedding.is_not(None),
            )
            .order_by(BrandDocument.embedding.cosine_distance(emb))
            .limit(k)
        )
        rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        return BRAND_SUMMARY

    formatted = "\n\n".join(
        f"[§{r.section or '—'}] {r.content}" for r in rows
    )
    return f"{BRAND_SUMMARY}\n\n--- Manual de marca (pasajes relevantes) ---\n{formatted}"
