"""Publicación en Instagram/Facebook vía Meta Graph API.

Flujo IG Business:
1. POST /{ig-user-id}/media  → crea container (image_url + caption)
2. POST /{ig-user-id}/media_publish con creation_id → publica

Carrusel:
1. Crear N containers con is_carousel_item=true
2. Crear container padre con children=ids, media_type=CAROUSEL
3. Publicar padre

Stories:
- media_type=STORIES para imágenes (soporta también VIDEO)
"""
from __future__ import annotations

import logging

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com"


async def _post(path: str, data: dict) -> dict:
    url = f"{GRAPH_BASE}/{settings.meta_api_version}/{path}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            data={**data, "access_token": settings.meta_access_token},
        )
        resp.raise_for_status()
        return resp.json()


async def _get(path: str, params: dict | None = None) -> dict:
    url = f"{GRAPH_BASE}/{settings.meta_api_version}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            url,
            params={**(params or {}), "access_token": settings.meta_access_token},
        )
        resp.raise_for_status()
        return resp.json()


async def ig_publish_image(image_url: str, caption: str) -> str:
    ig_id = settings.meta_ig_business_id
    container = await _post(
        f"{ig_id}/media",
        {"image_url": image_url, "caption": caption},
    )
    published = await _post(
        f"{ig_id}/media_publish",
        {"creation_id": container["id"]},
    )
    return published["id"]


async def ig_publish_carousel(image_urls: list[str], caption: str) -> str:
    ig_id = settings.meta_ig_business_id
    child_ids: list[str] = []
    for url in image_urls:
        c = await _post(
            f"{ig_id}/media",
            {"image_url": url, "is_carousel_item": "true"},
        )
        child_ids.append(c["id"])
    parent = await _post(
        f"{ig_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
        },
    )
    published = await _post(
        f"{ig_id}/media_publish",
        {"creation_id": parent["id"]},
    )
    return published["id"]


async def ig_publish_story(image_url: str) -> str:
    ig_id = settings.meta_ig_business_id
    container = await _post(
        f"{ig_id}/media",
        {"image_url": image_url, "media_type": "STORIES"},
    )
    published = await _post(
        f"{ig_id}/media_publish",
        {"creation_id": container["id"]},
    )
    return published["id"]


async def fb_publish_photo(image_url: str, caption: str) -> str:
    page_id = settings.meta_fb_page_id
    resp = await _post(
        f"{page_id}/photos",
        {"url": image_url, "caption": caption},
    )
    return resp["post_id"]


async def ig_insights(period: str = "last_7_days") -> dict:
    """Métricas de cuenta IG en el período indicado."""
    ig_id = settings.meta_ig_business_id
    metrics = "impressions,reach,profile_views,follower_count"
    return await _get(
        f"{ig_id}/insights",
        {"metric": metrics, "period": "day"},
    )


async def ig_media_insights(media_id: str) -> dict:
    metrics = "impressions,reach,saved,likes,comments,shares"
    return await _get(f"{media_id}/insights", {"metric": metrics})
