"""Estado de configuracion visible desde el dashboard."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


def present(value: str) -> bool:
    return bool(value and not value.startswith("change-me") and value != "...")


@router.get("/deployment")
def deployment_settings() -> dict:
    api_base = settings.next_public_api_base_url.rstrip("/")
    webhook_url = f"{api_base}/webhook/twilio" if api_base else ""

    return {
        "environment": settings.app_env,
        "tenant_id": settings.tenant_id,
        "dashboard_domain": settings.bot_estiv_dashboard_domain,
        "api_domain": settings.bot_estiv_api_domain,
        "api_base_url": settings.next_public_api_base_url,
        "twilio_webhook_url": webhook_url,
        "brand_logo_path": settings.brand_logo_path,
        "brand_manual_path": settings.brand_manual_path,
        "checks": {
            "database_url": present(settings.database_url),
            "database_url_sync": present(settings.database_url_sync),
            "redis_url": present(settings.redis_url),
            "google_api_key": present(settings.google_api_key),
            "twilio_account_sid": present(settings.twilio_account_sid),
            "twilio_auth_token": present(settings.twilio_auth_token),
            "twilio_whatsapp_from": present(settings.twilio_whatsapp_from),
            "twilio_whatsapp_to": present(settings.twilio_whatsapp_to),
            "meta_access_token": present(settings.meta_access_token),
            "meta_ad_account_id": present(settings.meta_ad_account_id),
            "meta_ig_business_id": present(settings.meta_ig_business_id),
            "meta_fb_page_id": present(settings.meta_fb_page_id),
            "s3_bucket": present(settings.s3_bucket),
            "s3_public_base_url": present(settings.s3_public_base_url),
            "sentry_dsn": present(settings.sentry_dsn),
        },
    }
