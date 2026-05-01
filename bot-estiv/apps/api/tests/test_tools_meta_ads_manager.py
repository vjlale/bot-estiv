"""Tests de agents/meta_ads_manager.py — apply_action y plan_changes mockeados."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot_estiv.agents.meta_ads_manager import AdsAction, AdsPlan, apply_action, plan_changes


# ---------------------------------------------------------------------------
# apply_action — routing a meta_ads según kind
# ---------------------------------------------------------------------------

def test_apply_action_pause():
    action = AdsAction(kind="pause", campaign_id="cmp_123", reason="bajo ROAS")
    with patch("bot_estiv.agents.meta_ads_manager.meta_ads.pause_campaign") as mock_pause:
        result = apply_action(action)
    mock_pause.assert_called_once_with("cmp_123")
    assert result == {"campaign_id": "cmp_123", "ok": True}


def test_apply_action_activate():
    action = AdsAction(kind="activate", campaign_id="cmp_456", reason="temporada alta")
    with patch("bot_estiv.agents.meta_ads_manager.meta_ads.activate_campaign") as mock_act:
        result = apply_action(action)
    mock_act.assert_called_once_with("cmp_456")
    assert result == {"campaign_id": "cmp_456", "ok": True}


def test_apply_action_update_budget():
    action = AdsAction(
        kind="update_budget",
        campaign_id="cmp_789",
        daily_budget_cents=300000,
        reason="aumentar en temporada",
    )
    with patch("bot_estiv.agents.meta_ads_manager.meta_ads.update_daily_budget") as mock_budget:
        result = apply_action(action)
    mock_budget.assert_called_once_with("cmp_789", 300000)
    assert result["ok"] is True


def test_apply_action_create():
    action = AdsAction(
        kind="create",
        name="GW_Pérgolas_2024",
        objective="OUTCOME_TRAFFIC",
        daily_budget_cents=200000,
        reason="nueva campaña primavera",
    )
    with patch(
        "bot_estiv.agents.meta_ads_manager.meta_ads.create_campaign", return_value="new_cmp_id"
    ) as mock_create:
        result = apply_action(action)
    mock_create.assert_called_once_with(
        "GW_Pérgolas_2024",
        objective="OUTCOME_TRAFFIC",
        daily_budget_cents=200000,
    )
    assert result == {"campaign_id": "new_cmp_id", "status": "paused"}


def test_apply_action_duplicate():
    action = AdsAction(
        kind="duplicate",
        campaign_id="cmp_src",
        name="GW_Copia_Verano",
        reason="probar nueva audiencia",
    )
    with patch(
        "bot_estiv.agents.meta_ads_manager.meta_ads.duplicate_campaign",
        return_value="new_dup_id",
    ) as mock_dup:
        result = apply_action(action)
    mock_dup.assert_called_once_with("cmp_src", "GW_Copia_Verano")
    assert result == {"campaign_id": "new_dup_id"}


def test_apply_action_create_requires_name():
    action = AdsAction(
        kind="create",
        name=None,  # falta name
        objective="OUTCOME_TRAFFIC",
        daily_budget_cents=200000,
        reason="sin nombre",
    )
    with pytest.raises(ValueError):
        apply_action(action)


# ---------------------------------------------------------------------------
# plan_changes — usa LLM mockeado
# ---------------------------------------------------------------------------

async def test_plan_changes_returns_ads_plan():
    fake_plan = AdsPlan(
        actions=[
            AdsAction(kind="pause", campaign_id="cmp_001", reason="ROAS < 1.5")
        ],
        summary="Pausar campañas de bajo rendimiento",
        expected_impact="Reducción de 20% del gasto sin pérdida de conversiones",
    )

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=fake_plan)

    with (
        patch("bot_estiv.agents.meta_ads_manager.meta_ads.list_campaigns", return_value=[]),
        patch("bot_estiv.agents.meta_ads_manager.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.meta_ads_manager.build_chain", return_value=mock_chain),
    ):
        result = await plan_changes("pausá lo que no anda")

    assert isinstance(result, AdsPlan)
    assert len(result.actions) == 1
    assert result.actions[0].kind == "pause"


async def test_plan_changes_handles_meta_api_failure():
    """Si meta_ads.list_campaigns falla, debe seguir funcionando con lista vacía."""
    fake_plan = AdsPlan(
        actions=[],
        summary="Sin campañas activas",
        expected_impact="Nulo",
    )

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=fake_plan)

    with (
        patch("bot_estiv.agents.meta_ads_manager.meta_ads.list_campaigns", side_effect=Exception("no creds")),
        patch("bot_estiv.agents.meta_ads_manager.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.meta_ads_manager.build_chain", return_value=mock_chain),
    ):
        result = await plan_changes("revisá las campañas")

    assert isinstance(result, AdsPlan)


# ---------------------------------------------------------------------------
# AdsAction — validación del modelo Pydantic
# ---------------------------------------------------------------------------

def test_ads_action_valid_kinds():
    for kind in ("create", "pause", "activate", "update_budget", "duplicate"):
        action = AdsAction(kind=kind, reason="test")
        assert action.kind == kind


def test_ads_plan_default_empty_actions():
    plan = AdsPlan(summary="test", expected_impact="nada")
    assert plan.actions == []
