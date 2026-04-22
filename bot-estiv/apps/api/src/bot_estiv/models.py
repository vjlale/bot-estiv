"""Modelos de base de datos."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class PostFormat(str, enum.Enum):
    IG_FEED_PORTRAIT = "ig_feed_portrait"
    IG_FEED_SQUARE = "ig_feed_square"
    IG_STORY = "ig_story"
    IG_REEL = "ig_reel"
    FB_FEED = "fb_feed"
    CAROUSEL = "carousel"
    VIDEO_STORY = "video_story"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp")
    user_wa_id: Mapped[str] = mapped_column(String(64), index=True)
    thread_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_message_at: Mapped[datetime] = mapped_column(server_default=func.now())

    messages: Mapped[list[Message]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))  # user|assistant|system|agent
    agent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    media_urls: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    title: Mapped[str] = mapped_column(String(256))
    caption: Mapped[str] = mapped_column(Text)
    hashtags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    format: Mapped[PostFormat] = mapped_column(Enum(PostFormat))
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus), default=PostStatus.DRAFT, index=True
    )
    pillar: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    meta_post_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand_check: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_agent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    assets: Mapped[list[Asset]] = relationship(back_populates="post", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    kind: Mapped[str] = mapped_column(String(32))  # image|video|pdf
    url: Mapped[str] = mapped_column(String(1024))
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slide_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    post: Mapped[Post] = relationship(back_populates="assets")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), index=True
    )
    requested_to_wa_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(256))
    objective: Mapped[str] = mapped_column(String(64))
    meta_campaign_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    daily_budget_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="paused", index=True)
    audience: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class BrandDocument(Base):
    """Chunks del manual de marca y documentos para RAG."""

    __tablename__ = "brand_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    source: Mapped[str] = mapped_column(String(256))
    section: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    source: Mapped[str] = mapped_column(String(32))  # ig|fb|ads
    period_start: Mapped[datetime]
    period_end: Mapped[datetime]
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)


class SourceAsset(Base):
    """Fotos reales de obras subidas por el cliente (WhatsApp o dashboard).

    Se agrupan por `project_tag` (ej: "cerco-mendiolaza") para que luego el
    RealPhotoCurator pueda construir carruseles editoriales a partir de un set.
    """

    __tablename__ = "source_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), index=True
    )
    # ej "cerco-mendiolaza". Puede ser None hasta que el usuario taguee.
    project_tag: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # ej "whatsapp" | "dashboard" | "scraper"
    source_channel: Mapped[str] = mapped_column(String(32), default="whatsapp")
    # URL donde vive el archivo (S3, file://, etc.)
    url: Mapped[str] = mapped_column(String(1024))
    kind: Mapped[str] = mapped_column(String(32), default="image")  # image|video
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # caption recibido junto con la foto (ej del WhatsApp)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_wa_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
