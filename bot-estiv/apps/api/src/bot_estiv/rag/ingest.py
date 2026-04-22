"""Ingesta del manual de marca en pgvector.

Uso:
    python -m bot_estiv.rag.ingest

Parte el manual en chunks por sección numerada (1.1, 1.2, 2.1 ...) y
calcula embeddings con Gemini Embedding 001 (768 dims, configurable).
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from sqlalchemy import select

from ..config import settings
from ..db import AsyncSessionLocal
from ..llm import get_embeddings
from ..models import BrandDocument, Tenant

logger = logging.getLogger(__name__)

SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+\S")


def chunk_manual(text: str) -> list[tuple[str, str]]:
    """Retorna list of (section_id, content)."""
    lines = text.splitlines()
    chunks: list[tuple[str, str]] = []
    current_section = "intro"
    current_buffer: list[str] = []
    for line in lines:
        m = SECTION_RE.match(line.strip())
        if m:
            if current_buffer:
                chunks.append((current_section, "\n".join(current_buffer).strip()))
            current_section = m.group(1)
            current_buffer = [line]
        else:
            current_buffer.append(line)
    if current_buffer:
        chunks.append((current_section, "\n".join(current_buffer).strip()))
    return [(s, c) for s, c in chunks if c]


async def _ensure_tenant(session) -> "Tenant":
    result = await session.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(slug=settings.tenant_id, name=settings.tenant_id.replace("-", " ").title())
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
    return tenant


async def ingest_manual(path: Path | None = None) -> int:
    path = path or settings.brand_manual_abs
    if not Path(path).exists():
        raise FileNotFoundError(f"Manual no encontrado: {path}")

    text = Path(path).read_text(encoding="utf-8")
    chunks = chunk_manual(text)
    embeddings_client = get_embeddings()

    async with AsyncSessionLocal() as session:
        tenant = await _ensure_tenant(session)

        # Limpieza previa por fuente
        from sqlalchemy import delete

        await session.execute(
            delete(BrandDocument).where(
                BrandDocument.tenant_id == tenant.id,
                BrandDocument.source == str(path.name),
            )
        )

        vectors = embeddings_client.embed_documents([c for _, c in chunks])
        for (section, content), vec in zip(chunks, vectors):
            session.add(
                BrandDocument(
                    tenant_id=tenant.id,
                    source=path.name,
                    section=section,
                    content=content,
                    embedding=vec,
                    metadata_json={"chars": len(content)},
                )
            )
        await session.commit()

    logger.info("brand_rag.ingested", extra={"chunks": len(chunks), "source": path.name})
    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = asyncio.run(ingest_manual())
    print(f"Ingestados {n} chunks del manual de marca.")
