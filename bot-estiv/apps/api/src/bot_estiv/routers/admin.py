"""Endpoints de administración: RAG, migraciones, estado del sistema."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from ..db import AsyncSessionLocal
from ..models import BrandDocument, Tenant
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest-brand")
async def ingest_brand_manual() -> dict:
    """Ingesta el manual de marca en pgvector.

    Corre el pipeline: chunking por sección → embeddings Gemini → inserción en BrandDocument.
    Idempotente: borra los docs anteriores del mismo source antes de reinsertar.
    """
    from ..rag.ingest import ingest_manual

    try:
        n = await ingest_manual()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("rag.ingest_failed")
        raise HTTPException(status_code=500, detail=f"Ingestión fallida: {exc}") from exc

    return {"ok": True, "chunks_ingested": n}


@router.get("/rag-status")
async def rag_status() -> dict:
    """Muestra cuántos chunks de marca hay en la BD y si el RAG está listo."""
    async with AsyncSessionLocal() as session:
        tenant_row = (
            await session.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
        ).scalar_one_or_none()

        if tenant_row is None:
            return {"ready": False, "chunks": 0, "tenant": settings.tenant_id}

        count = (
            await session.execute(
                select(func.count()).select_from(BrandDocument).where(
                    BrandDocument.tenant_id == tenant_row.id,
                    BrandDocument.embedding.is_not(None),
                )
            )
        ).scalar_one()

    return {
        "ready": count > 0,
        "chunks": count,
        "tenant": settings.tenant_id,
        "manual_path": str(settings.brand_manual_abs),
    }
