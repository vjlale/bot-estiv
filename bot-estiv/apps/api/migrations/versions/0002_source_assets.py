"""source_assets table

Revision ID: 0002_source_assets
Revises: 0001_init
Create Date: 2026-04-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_source_assets"
down_revision: str | None = "0001_init"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "source_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("project_tag", sa.String(128), nullable=True, index=True),
        sa.Column("source_channel", sa.String(32), nullable=False, server_default="whatsapp"),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="image"),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("uploaded_by_wa_id", sa.String(64), nullable=True, index=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("source_assets")
