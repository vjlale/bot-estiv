"""Storage abstracción: S3 / Cloudflare R2 con fallback local."""
from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from pathlib import Path

import boto3
from botocore.config import Config

from ..config import settings

logger = logging.getLogger(__name__)

LOCAL_MEDIA_DIR = Path("/media")
LOCAL_FALLBACK_DIR = Path.cwd() / "media_local"


def _use_s3() -> bool:
    return bool(settings.s3_access_key_id and settings.s3_secret_access_key and settings.s3_bucket)


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region or "auto",
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=Config(signature_version="s3v4"),
    )


def upload_bytes(data: bytes, key: str, content_type: str | None = None) -> str:
    content_type = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
    if _use_s3():
        client = _client()
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        base = settings.s3_public_base_url.rstrip("/")
        return f"{base}/{key}" if base else f"s3://{settings.s3_bucket}/{key}"

    base = LOCAL_MEDIA_DIR if LOCAL_MEDIA_DIR.exists() else LOCAL_FALLBACK_DIR
    target = base / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    logger.info("storage.local_saved", extra={"path": str(target)})
    public_base = settings.next_public_api_base_url.rstrip("/")
    if base == LOCAL_MEDIA_DIR and public_base:
        return f"{public_base}/media/{key}"
    return f"file://{target}"


def new_key(prefix: str, ext: str) -> str:
    return f"{prefix}/{uuid.uuid4().hex}.{ext.lstrip('.')}"
