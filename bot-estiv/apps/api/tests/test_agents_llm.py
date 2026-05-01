"""Tests para los agentes que usan LLM (Gemini), usando build_chain mockeado."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot_estiv.schemas import (
    AnalyticsReport,
    CopyDraft,
    WeeklyPlan,
    WeeklyPlanEntry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chain(return_value):
    """Crea una cadena falsa cuyo ainvoke devuelve el valor dado."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=return_value)
    return chain


# ---------------------------------------------------------------------------
# agents/copywriter.py
# ---------------------------------------------------------------------------

async def test_copywriter_run_returns_copy_draft():
    from bot_estiv.agents import copywriter

    expected = CopyDraft(
        title="Pérgolas que perduran generaciones",
        caption="La nobleza del Quebracho resiste el paso del tiempo.",
        hashtags=["#GardensWood", "#Quebracho", "#Pergolas"] * 6,
        cta="Conocé más en nuestro showroom.",
    )
    chain = _make_chain(expected)

    with (
        patch("bot_estiv.agents.copywriter.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.copywriter.build_chain", return_value=chain),
    ):
        result = await copywriter.run(topic="pérgolas")

    assert isinstance(result, CopyDraft)
    assert result.title == expected.title
    chain.ainvoke.assert_called_once()


async def test_copywriter_run_passes_pillar_and_content_type():
    from bot_estiv.agents import copywriter

    expected = CopyDraft(
        title="Diseño que inspira",
        caption="Cada detalle refleja la artesanía.",
        hashtags=["#GardensWood"] * 16,
        cta=None,
    )
    chain = _make_chain(expected)

    with (
        patch("bot_estiv.agents.copywriter.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.copywriter.build_chain", return_value=chain) as mock_build,
    ):
        await copywriter.run(topic="decks", pillar="diseno", content_type="educativo")

    invoke_args = chain.ainvoke.call_args[0][0]
    assert "diseno" in invoke_args["input"]
    assert "educativo" in invoke_args["input"]


async def test_copywriter_run_without_pillar():
    from bot_estiv.agents import copywriter

    expected = CopyDraft(
        title="Fogoneros de Quebracho",
        caption="Calor y diseño.",
        hashtags=["#GardensWood"] * 16,
        cta=None,
    )
    chain = _make_chain(expected)

    with (
        patch("bot_estiv.agents.copywriter.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.copywriter.build_chain", return_value=chain),
    ):
        result = await copywriter.run(topic="fogoneros")

    assert isinstance(result, CopyDraft)


# ---------------------------------------------------------------------------
# agents/campaign_planner.py
# ---------------------------------------------------------------------------

async def test_campaign_planner_returns_weekly_plan():
    from bot_estiv.agents import campaign_planner

    expected = WeeklyPlan(
        week_of="2024-W15",
        entries=[
            WeeklyPlanEntry(
                day="lunes",
                slot="19:00",
                format="ig_feed_portrait",
                pillar="durabilidad",
                content_type="educativo",
                topic="Cuidados del Quebracho en invierno",
            ),
            WeeklyPlanEntry(
                day="miércoles",
                slot="12:00",
                format="carousel_portrait",
                pillar="diseno",
                content_type="educativo",
                topic="Tipos de maderas para exterior",
            ),
            WeeklyPlanEntry(
                day="viernes",
                slot="18:00",
                format="ig_story",
                pillar="experiencia",
                content_type="temporada",
                topic="Instalación en Córdoba",
            ),
            WeeklyPlanEntry(
                day="sábado",
                slot="10:00",
                format="carousel_portrait",
                pillar="diseno",
                content_type="promocional",
                topic="Nueva pérgola modelo 2024",
            ),
        ],
        summary="Semana balanceada con foco en educación del material.",
    )
    chain = _make_chain(expected)

    with (
        patch("bot_estiv.agents.campaign_planner.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.campaign_planner.build_chain", return_value=chain),
    ):
        result = await campaign_planner.plan_week()

    assert isinstance(result, WeeklyPlan)
    assert len(result.entries) == 4
    assert result.week_of == "2024-W15"


async def test_campaign_planner_passes_current_date():
    from bot_estiv.agents import campaign_planner

    expected = WeeklyPlan(
        week_of="2024-W52",
        entries=[
            WeeklyPlanEntry(
                day="lunes",
                slot="19:00",
                format="ig_feed_portrait",
                pillar="durabilidad",
                content_type="educativo",
                topic="Navidad al aire libre",
            )
        ] * 4,
        summary="Semana navideña.",
    )
    chain = _make_chain(expected)

    test_date = datetime(2024, 12, 25)

    with (
        patch("bot_estiv.agents.campaign_planner.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.campaign_planner.build_chain", return_value=chain),
    ):
        result = await campaign_planner.plan_week(today=test_date)

    invoke_input = chain.ainvoke.call_args[0][0]["input"]
    assert "2024-12-25" in invoke_input


# ---------------------------------------------------------------------------
# agents/analytics.py
# ---------------------------------------------------------------------------

async def test_analytics_weekly_report_returns_report():
    from bot_estiv.agents import analytics

    expected = AnalyticsReport(
        period="2024-W15",
        kpis={"reach": 12000, "engagement_rate": 0.045, "cpa": 8.5},
        top_posts=[{"id": "abc", "reach": 5000}],
        recommendations=[
            "Publicar más carruseles educativos los martes 19hs.",
            "El pilar Diseño tiene +42% engagement vs Durabilidad.",
        ],
    )
    chain = _make_chain(expected)

    with (
        patch("bot_estiv.agents.analytics.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.analytics.meta_graph.ig_insights", new=AsyncMock(return_value={})),
        patch("bot_estiv.agents.analytics.meta_ads.account_insights", return_value=[]),
        patch("bot_estiv.agents.analytics.build_chain", return_value=chain),
    ):
        result = await analytics.weekly_report()

    assert isinstance(result, AnalyticsReport)
    assert len(result.recommendations) == 2


async def test_analytics_handles_meta_api_failure():
    """El agente debe funcionar aunque las APIs de Meta fallen."""
    from bot_estiv.agents import analytics

    expected = AnalyticsReport(
        period="2024-W15",
        kpis={},
        top_posts=[],
        recommendations=["Revisar las credenciales de Meta API."],
    )
    chain = _make_chain(expected)

    with (
        patch("bot_estiv.agents.analytics.retrieve_brand_context", new=AsyncMock(return_value="ctx")),
        patch("bot_estiv.agents.analytics.meta_graph.ig_insights", new=AsyncMock(side_effect=Exception("no token"))),
        patch("bot_estiv.agents.analytics.meta_ads.account_insights", side_effect=Exception("no creds")),
        patch("bot_estiv.agents.analytics.build_chain", return_value=chain),
    ):
        result = await analytics.weekly_report()

    assert isinstance(result, AnalyticsReport)


# ---------------------------------------------------------------------------
# agents/content_designer.py — build_visual_prompt y _pick_template son puras
# ---------------------------------------------------------------------------

def test_build_visual_prompt_without_slide():
    from bot_estiv.agents.content_designer import build_visual_prompt

    prompt = build_visual_prompt("pérgola de quebracho en jardín")
    assert "pérgola de quebracho en jardín" in prompt
    assert "no text in image" in prompt.lower()


def test_build_visual_prompt_with_slide():
    from bot_estiv.agents.content_designer import build_visual_prompt
    from bot_estiv.schemas import SlideBrief

    slide = SlideBrief(
        index=1,
        headline="Diseñado para Durar",
        body="La nobleza del Quebracho.",
        visual_prompt="mesa exterior de quebracho al atardecer",
    )
    prompt = build_visual_prompt("mesa exterior", slide)
    assert "mesa exterior de quebracho" in prompt
    assert "Diseñado para Durar" in prompt
    assert "Do NOT render text" in prompt


def test_pick_template_uses_slide_template():
    from bot_estiv.agents.content_designer import _pick_template
    from bot_estiv.schemas import SlideBrief

    slide = SlideBrief(
        index=1,
        headline="Título",
        visual_prompt="foto",
        template="spec_card",
    )
    result = _pick_template(slide, "editorial_hero", position_1based=1)
    assert result == "spec_card"


def test_pick_template_uses_position_map_when_no_slide_template():
    from bot_estiv.agents.content_designer import _pick_template
    from bot_estiv.schemas import SlideBrief

    slide = SlideBrief(index=0, headline="", visual_prompt="foto", template=None)
    # posición 1 → cover_hero según _ROLE_TEMPLATE_BY_INDEX
    assert _pick_template(slide, "editorial_hero", position_1based=1) == "cover_hero"
    # posición 2 → minimal_stamp
    assert _pick_template(slide, "editorial_hero", position_1based=2) == "minimal_stamp"
    # posición 99 → default
    assert _pick_template(slide, "editorial_hero", position_1based=99) == "editorial_hero"


def test_pick_template_none_slide_uses_default():
    from bot_estiv.agents.content_designer import _pick_template

    result = _pick_template(None, "cover_hero", position_1based=5)
    assert result == "spec_card"  # posición 5 → spec_card en el mapa
