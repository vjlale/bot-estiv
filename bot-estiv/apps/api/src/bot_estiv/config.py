"""Configuración central cargada desde variables de entorno."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    app_env: str = "development"
    app_name: str = "bot-estiv"
    log_level: str = "INFO"
    tenant_id: str = "gardens-wood"
    bot_estiv_dashboard_domain: str = ""
    bot_estiv_api_domain: str = ""
    next_public_api_base_url: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bot_estiv"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/bot_estiv"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Google Gemini (único proveedor LLM)
    google_api_key: str = ""
    # Modelo de texto/razonamiento — económico + smart
    gemini_model: str = "gemini-3.1-flash-lite-preview"
    # Generación de imágenes — Nano Banana 2
    gemini_image_model: str = "gemini-3.1-flash-image-preview"
    # Embeddings para RAG (768 dims = más barato + suficiente para manual de marca)
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dim: int = 768

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    twilio_whatsapp_to: str = ""

    # Meta
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_access_token: str = ""
    meta_ad_account_id: str = ""
    meta_ig_business_id: str = ""
    meta_fb_page_id: str = ""
    meta_api_version: str = "v19.0"

    # S3 / R2
    s3_endpoint_url: str = ""
    s3_region: str = "auto"
    s3_bucket: str = "bot-estiv-media"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_public_base_url: str = ""

    # Brand
    brand_logo_path: str = "../../Branding/LOGOCOMPLETO.png"
    brand_manual_path: str = "../../Branding/Manual de Identidad de Marca_ Gardens Wood.txt"

    # Figma (plantillas de overlay como fuente de verdad)
    figma_access_token: str = ""
    figma_templates_file_key: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""  # ej: https://api.tudominio.com (sin /webhook/telegram)

    # Monitoring
    sentry_dsn: str = ""

    @property
    def brand_logo_abs(self) -> Path:
        return Path(self.brand_logo_path).resolve()

    @property
    def brand_manual_abs(self) -> Path:
        return Path(self.brand_manual_path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
