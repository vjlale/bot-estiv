"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-04-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("channel", sa.String(32), server_default="whatsapp"),
        sa.Column("user_wa_id", sa.String(64), nullable=False, index=True),
        sa.Column("thread_id", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False, index=True),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("agent", sa.String(64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("media_urls", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    post_status = postgresql.ENUM(
        "draft", "pending_approval", "approved", "rejected", "scheduled", "published", "failed",
        name="poststatus",
        create_type=False,
    )
    post_format = postgresql.ENUM(
        "ig_feed_portrait", "ig_feed_square", "ig_story", "ig_reel",
        "fb_feed", "carousel", "video_story",
        name="postformat",
        create_type=False,
    )
    post_status.create(op.get_bind(), checkfirst=True)
    post_format.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hashtags", sa.JSON(), nullable=True),
        sa.Column("format", post_format, nullable=False),
        sa.Column("status", post_status, nullable=False, server_default="draft", index=True),
        sa.Column("pillar", sa.String(32), nullable=True),
        sa.Column("content_type", sa.String(32), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_post_id", sa.String(128), nullable=True),
        sa.Column("brand_check", sa.JSON(), nullable=True),
        sa.Column("created_by_agent", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id"), nullable=True, index=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("slide_index", sa.Integer(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id"), nullable=False, index=True),
        sa.Column("requested_to_wa_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending", index=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("objective", sa.String(64), nullable=False),
        sa.Column("meta_campaign_id", sa.String(128), nullable=True, index=True),
        sa.Column("daily_budget_cents", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="paused", index=True),
        sa.Column("audience", sa.JSON(), nullable=True),
        sa.Column("metrics_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "brand_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source", sa.String(256), nullable=False),
        sa.Column("section", sa.String(128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(
        "CREATE INDEX ix_brand_documents_embedding "
        "ON brand_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("analytics_snapshots")
    op.execute("DROP INDEX IF EXISTS ix_brand_documents_embedding")
    op.drop_table("brand_documents")
    op.drop_table("campaigns")
    op.drop_table("approvals")
    op.drop_table("assets")
    op.drop_table("posts")
    op.execute("DROP TYPE IF EXISTS postformat")
    op.execute("DROP TYPE IF EXISTS poststatus")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("tenants")
