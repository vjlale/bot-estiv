"""Biblioteca de FOTOS REALES de obras (Source Assets).

Endpoints:
- GET  /source-assets              listar (filtro opcional por project_tag)
- GET  /source-assets/projects     proyectos con conteo de fotos
- POST /source-assets/upload       subir multipart desde dashboard
- POST /source-assets/{id}/tag     asignar/editar project_tag
- POST /source-assets/{id}/delete  borrado lógico (marca metadata)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import AsyncSessionLocal, get_session
from ..models import SourceAsset, Tenant
from ..tools import storage

router = APIRouter(prefix="/source-assets", tags=["source-assets"])


# ========== Schemas ==========


class SourceAssetOut(BaseModel):
    id: uuid.UUID
    project_tag: str | None = None
    source_channel: str
    url: str
    kind: str
    width: int | None = None
    height: int | None = None
    caption: str | None = None
    uploaded_by_wa_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    project_tag: str
    count: int
    last_upload: datetime


class TagUpdate(BaseModel):
    project_tag: str | None = None


# ========== Helper compartido (también usado por el webhook) ==========


async def ensure_default_tenant(session: AsyncSession) -> Tenant:
    """Crea si hace falta el tenant configurado en settings.tenant_id."""
    row = (
        await session.execute(select(Tenant).where(Tenant.slug == settings.tenant_id))
    ).scalar_one_or_none()
    if row is None:
        row = Tenant(slug=settings.tenant_id, name=settings.tenant_id.replace("-", " ").title())
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def create_source_asset(
    url: str,
    *,
    kind: str = "image",
    source_channel: str = "whatsapp",
    project_tag: str | None = None,
    caption: str | None = None,
    uploaded_by_wa_id: str | None = None,
    width: int | None = None,
    height: int | None = None,
    metadata: dict | None = None,
) -> SourceAsset:
    """Util para que otros módulos (webhook, worker) creen SourceAssets."""
    async with AsyncSessionLocal() as session:
        tenant = await ensure_default_tenant(session)
        asset = SourceAsset(
            tenant_id=tenant.id,
            project_tag=project_tag,
            source_channel=source_channel,
            url=url,
            kind=kind,
            width=width,
            height=height,
            caption=caption,
            uploaded_by_wa_id=uploaded_by_wa_id,
            metadata_json=metadata,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        return asset


# ========== Endpoints ==========


@router.get("", response_model=list[SourceAssetOut])
async def list_source_assets(
    project_tag: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int = Query(default=200, le=500),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(SourceAsset).order_by(SourceAsset.created_at.desc()).limit(limit)
    if project_tag:
        stmt = stmt.where(SourceAsset.project_tag == project_tag)
    if kind:
        stmt = stmt.where(SourceAsset.kind == kind)
    return (await session.execute(stmt)).scalars().all()


@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects(session: AsyncSession = Depends(get_session)):
    stmt = (
        select(
            SourceAsset.project_tag,
            func.count(SourceAsset.id).label("count"),
            func.max(SourceAsset.created_at).label("last_upload"),
        )
        .where(SourceAsset.project_tag.is_not(None))
        .group_by(SourceAsset.project_tag)
        .order_by(func.max(SourceAsset.created_at).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        ProjectSummary(project_tag=r[0], count=int(r[1]), last_upload=r[2])
        for r in rows
        if r[0]
    ]


@router.post("/upload", response_model=SourceAssetOut)
async def upload_source_asset(
    file: UploadFile = File(...),
    project_tag: str | None = Form(default=None),
    caption: str | None = Form(default=None),
):
    raw = await file.read()
    ext = (file.filename or "").split(".")[-1].lower() if file.filename else "jpg"
    if ext not in ("png", "jpg", "jpeg", "webp", "mp4"):
        ext = "jpg"
    key = storage.new_key("source-assets/dashboard", ext)
    url = storage.upload_bytes(raw, key, content_type=file.content_type or "image/jpeg")

    # width/height si es imagen
    width: int | None = None
    height: int | None = None
    if ext in ("png", "jpg", "jpeg", "webp"):
        try:
            from PIL import Image
            import io as _io

            img = Image.open(_io.BytesIO(raw))
            width, height = img.size
        except Exception:  # noqa: BLE001
            pass

    asset = await create_source_asset(
        url=url,
        kind="image" if ext != "mp4" else "video",
        source_channel="dashboard",
        project_tag=project_tag,
        caption=caption,
        width=width,
        height=height,
    )
    return asset


@router.post("/{asset_id}/tag", response_model=SourceAssetOut)
async def update_tag(
    asset_id: uuid.UUID,
    body: TagUpdate,
    session: AsyncSession = Depends(get_session),
):
    row = (
        await session.execute(select(SourceAsset).where(SourceAsset.id == asset_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="source_asset no encontrado")
    row.project_tag = body.project_tag
    await session.commit()
    await session.refresh(row)
    return row
