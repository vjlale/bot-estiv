"""Meta Marketing API (Ads) - crear / pausar / actualizar campañas.

Usa el SDK oficial `facebook_business`. Todas las operaciones que mutan
estado requieren confirmación humana del Director antes de ejecutarse.
"""
from __future__ import annotations

import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


def _init_api():
    from facebook_business.api import FacebookAdsApi

    return FacebookAdsApi.init(
        app_id=settings.meta_app_id,
        app_secret=settings.meta_app_secret,
        access_token=settings.meta_access_token,
        api_version=settings.meta_api_version,
    )


def list_campaigns() -> list[dict]:
    from facebook_business.adobjects.adaccount import AdAccount

    _init_api()
    ad_account = AdAccount(settings.meta_ad_account_id)
    fields = [
        "id", "name", "objective", "status", "effective_status",
        "daily_budget", "lifetime_budget", "start_time", "stop_time",
    ]
    return [c.export_all_data() for c in ad_account.get_campaigns(fields=fields)]


def create_campaign(
    name: str,
    objective: str = "OUTCOME_TRAFFIC",
    daily_budget_cents: int = 200000,
    special_ad_categories: list[str] | None = None,
) -> str:
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign

    _init_api()
    ad_account = AdAccount(settings.meta_ad_account_id)
    params = {
        Campaign.Field.name: name,
        Campaign.Field.objective: objective,
        Campaign.Field.status: Campaign.Status.paused,
        Campaign.Field.daily_budget: daily_budget_cents,
        Campaign.Field.special_ad_categories: special_ad_categories or [],
    }
    campaign = ad_account.create_campaign(params=params)
    return campaign["id"]


def pause_campaign(campaign_id: str) -> None:
    from facebook_business.adobjects.campaign import Campaign

    _init_api()
    Campaign(campaign_id).api_update(params={Campaign.Field.status: Campaign.Status.paused})


def activate_campaign(campaign_id: str) -> None:
    from facebook_business.adobjects.campaign import Campaign

    _init_api()
    Campaign(campaign_id).api_update(params={Campaign.Field.status: Campaign.Status.active})


def update_daily_budget(campaign_id: str, daily_budget_cents: int) -> None:
    from facebook_business.adobjects.campaign import Campaign

    _init_api()
    Campaign(campaign_id).api_update(
        params={Campaign.Field.daily_budget: daily_budget_cents}
    )


def duplicate_campaign(campaign_id: str, new_name: str) -> str:
    from facebook_business.adobjects.campaign import Campaign

    _init_api()
    result = Campaign(campaign_id).create_copy(
        params={
            "deep_copy": True,
            "status_option": "PAUSED",
            "rename_options": {"rename_suffix": f" - {new_name}"},
        }
    )
    return result["copied_campaign_id"]


def campaign_insights(campaign_id: str, date_preset: str = "last_7_d") -> dict[str, Any]:
    from facebook_business.adobjects.campaign import Campaign

    _init_api()
    fields = [
        "campaign_name", "spend", "impressions", "clicks", "ctr",
        "cpc", "cpm", "reach", "frequency", "actions", "cost_per_action_type",
    ]
    insights = Campaign(campaign_id).get_insights(
        fields=fields, params={"date_preset": date_preset}
    )
    return insights[0].export_all_data() if insights else {}


def account_insights(date_preset: str = "last_7_d") -> list[dict[str, Any]]:
    from facebook_business.adobjects.adaccount import AdAccount

    _init_api()
    ad_account = AdAccount(settings.meta_ad_account_id)
    fields = ["campaign_name", "spend", "impressions", "clicks", "ctr", "cpc", "reach"]
    insights = ad_account.get_insights(
        fields=fields,
        params={"date_preset": date_preset, "level": "campaign"},
    )
    return [ins.export_all_data() for ins in insights]
