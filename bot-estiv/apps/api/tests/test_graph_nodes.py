"""Tests de los nodos individuales del grafo LangGraph y funciones auxiliares."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot_estiv.graph import (
    State,
    _route,
    node_chitchat,
    node_router,
    node_copywriter,
    node_brand_guardian,
    node_approval_decision,
    node_planner,
    node_ads,
    node_analytics,
    node_trends,
)
from bot_estiv.routers.webhook import _extract_project_tag


# ---------------------------------------------------------------------------
# _extract_project_tag (función pura del webhook)
# ---------------------------------------------------------------------------

def test_extract_project_tag_found():
    assert _extract_project_tag("Fotos del #cerco-mendiolaza terminado") == "cerco-mendiolaza"


def test_extract_project_tag_normalizes_lowercase():
    assert _extract_project_tag("#Pergola-Norte") == "pergola-norte"


def test_extract_project_tag_none_when_empty():
    assert _extract_project_tag("") is None


def test_extract_project_tag_none_when_no_hashtag():
    assert _extract_project_tag("Sin hashtag aquí") is None


def test_extract_project_tag_returns_first():
    assert _extract_project_tag("#primero y #segundo") == "primero"


# ---------------------------------------------------------------------------
# _route — lógica de routing del grafo
# ---------------------------------------------------------------------------

def test_route_create_post():
    state = {"routing": {"intent": "create_post"}}
    assert _route(state) == "copywriter"


def test_route_weekly_plan():
    state = {"routing": {"intent": "weekly_plan"}}
    assert _route(state) == "planner"


def test_route_ads_change():
    state = {"routing": {"intent": "ads_change"}}
    assert _route(state) == "ads"


def test_route_analytics():
    state = {"routing": {"intent": "analytics_report"}}
    assert _route(state) == "analytics"


def test_route_trends():
    state = {"routing": {"intent": "trend_ideas"}}
    assert _route(state) == "trends"


def test_route_approval_decision():
    state = {"routing": {"intent": "approval_decision"}}
    assert _route(state) == "approval_decision"


def test_route_chitchat():
    state = {"routing": {"intent": "chitchat"}}
    assert _route(state) == "chitchat"


def test_route_unknown_falls_back_to_chitchat():
    state = {"routing": {"intent": "algo_desconocido"}}
    assert _route(state) == "chitchat"


# ---------------------------------------------------------------------------
# node_chitchat — respuesta estática, sin dependencias externas
# ---------------------------------------------------------------------------

async def test_node_chitchat_sets_reply_text():
    state: State = {"user_text": "Hola", "user_wa_id": "+5491100000000", "messages": []}
    result = await node_chitchat(state)
    assert "reply_text" in result
    assert "Bot Estiv" in result["reply_text"]
    assert "Gardens Wood" in result["reply_text"]


# ---------------------------------------------------------------------------
# node_router — delega a director.classify
# ---------------------------------------------------------------------------

async def test_node_router_sets_routing():
    from bot_estiv.agents.director import RoutingDecision

    fake_decision = RoutingDecision(intent="chitchat")

    with patch("bot_estiv.graph.director.classify", return_value=fake_decision):
        state: State = {"user_text": "Hola", "user_wa_id": "+5491100000000", "messages": []}
        result = await node_router(state)

    assert result["routing"]["intent"] == "chitchat"


# ---------------------------------------------------------------------------
# node_copywriter — delega a copywriter.run
# ---------------------------------------------------------------------------

async def test_node_copywriter_sets_draft_copy():
    from bot_estiv.schemas import CopyDraft

    fake_draft = CopyDraft(
        title="El Quebracho que perdura",
        caption="Creamos el espacio de encuentro perfecto.",
        hashtags=["#GardensWood", "#Quebracho"],
        cta="Conocé más en nuestro showroom.",
    )

    with patch("bot_estiv.graph.copywriter.run", new=AsyncMock(return_value=fake_draft)):
        state: State = {
            "user_text": "carrusel de pérgolas",
            "user_wa_id": "+5491100000000",
            "messages": [],
            "routing": {"topic": "pérgolas", "pillar": "diseno", "content_type": "educativo"},
        }
        result = await node_copywriter(state)

    assert result["draft_copy"]["title"] == "El Quebracho que perdura"
    assert result["draft_copy"]["hashtags"] == ["#GardensWood", "#Quebracho"]


# ---------------------------------------------------------------------------
# node_brand_guardian — usa validate_copy real (sin LLM)
# ---------------------------------------------------------------------------

async def test_node_brand_guardian_passes_clean_copy():
    state: State = {
        "user_text": "",
        "user_wa_id": "",
        "messages": [],
        "draft_copy": {
            "title": "Pérgolas de Quebracho",
            "caption": "La nobleza del Quebracho resiste el paso del tiempo.",
            "hashtags": ["#GardensWood"] * 18,
            "cta": "Pedí asesoramiento.",
        },
    }
    result = await node_brand_guardian(state)
    assert "brand_check" in result
    assert "passed" in result["brand_check"]


async def test_node_brand_guardian_flags_forbidden_words():
    state: State = {
        "user_text": "",
        "user_wa_id": "",
        "messages": [],
        "draft_copy": {
            "title": "¡El mejor mueble increíble!",
            "caption": "¡Aprovechá esta oferta imperdible! El mejor producto.",
            "hashtags": ["#GardensWood"] * 18,
            "cta": None,
        },
    }
    result = await node_brand_guardian(state)
    assert result["brand_check"]["passed"] is False


# ---------------------------------------------------------------------------
# node_approval_decision — lógica de DB mockeada
# ---------------------------------------------------------------------------

async def test_node_approval_decision_missing_post_id():
    state: State = {
        "user_text": "",
        "user_wa_id": "",
        "messages": [],
        "routing": {"intent": "approval_decision", "post_id": None, "decision": "aprobar"},
    }
    result = await node_approval_decision(state)
    assert "No pude identificar" in result["reply_text"]


async def test_node_approval_decision_invalid_uuid():
    state: State = {
        "user_text": "",
        "user_wa_id": "",
        "messages": [],
        "routing": {"intent": "approval_decision", "post_id": "no-es-uuid", "decision": "aprobar"},
    }
    result = await node_approval_decision(state)
    assert "inválido" in result["reply_text"]


async def test_node_approval_decision_post_not_found():
    from bot_estiv.models import Post, Approval

    post_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result_mock
    mock_session.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_estiv.graph.AsyncSessionLocal", return_value=mock_factory):
        state: State = {
            "user_text": "",
            "user_wa_id": "",
            "messages": [],
            "routing": {
                "intent": "approval_decision",
                "post_id": post_id,
                "decision": "aprobar",
                "reason": None,
            },
        }
        result = await node_approval_decision(state)

    assert "No encuentro el post" in result["reply_text"]


def _make_graph_approval_session(fake_post, fake_approval):
    """Crea una AsyncSession mockeada que devuelve fake_post o fake_approval
    según la tabla que el stmt consulte, sin depender del orden de las llamadas."""
    mock_session = AsyncMock()

    def side_effect(stmt):
        result = MagicMock()
        try:
            table_name = stmt.get_final_froms()[0].name
        except (AttributeError, IndexError):
            table_name = ""
        if table_name == "approvals":
            result.scalar_one_or_none.return_value = fake_approval
        else:
            result.scalar_one_or_none.return_value = fake_post
        return result

    mock_session.execute = AsyncMock(side_effect=side_effect)
    mock_session.commit = AsyncMock()
    return mock_session


async def test_node_approval_decision_approve():
    from bot_estiv.models import Post, Approval, PostStatus

    post_id = str(uuid.uuid4())
    fake_post = MagicMock(spec=Post)
    fake_post.status = PostStatus.PENDING_APPROVAL
    fake_approval = MagicMock(spec=Approval)
    fake_approval.status = "pending"

    mock_session = _make_graph_approval_session(fake_post, fake_approval)

    mock_factory = MagicMock()
    mock_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.__aexit__ = AsyncMock(return_value=False)

    with patch("bot_estiv.graph.AsyncSessionLocal", return_value=mock_factory):
        state: State = {
            "user_text": "",
            "user_wa_id": "",
            "messages": [],
            "routing": {
                "intent": "approval_decision",
                "post_id": post_id,
                "decision": "aprobar",
                "reason": None,
            },
        }
        result = await node_approval_decision(state)

    assert fake_post.status == PostStatus.APPROVED
    assert "aprobado" in result["reply_text"]


# ---------------------------------------------------------------------------
# node_planner — delega a campaign_planner.plan_week
# ---------------------------------------------------------------------------

async def test_node_planner_sets_reply_text():
    from bot_estiv.schemas import WeeklyPlan, WeeklyPlanEntry

    fake_plan = WeeklyPlan(
        week_of="2024-W01",
        entries=[
            WeeklyPlanEntry(
                day="lunes",
                slot="19:00",
                format="ig_feed_portrait",
                pillar="durabilidad",
                content_type="educativo",
                topic="Cuidados del Quebracho en verano",
            )
        ],
        summary="Semana enfocada en durabilidad y educación del material.",
    )

    with patch("bot_estiv.graph.campaign_planner.plan_week", new=AsyncMock(return_value=fake_plan)):
        state: State = {"user_text": "planificá la semana", "user_wa_id": "", "messages": []}
        result = await node_planner(state)

    assert "Plan editorial" in result["reply_text"]
    assert "report" in result


# ---------------------------------------------------------------------------
# node_ads — delega a meta_ads_manager.plan_changes
# ---------------------------------------------------------------------------

async def test_node_ads_sets_reply_text():
    from bot_estiv.agents.meta_ads_manager import AdsPlan, AdsAction

    fake_plan = AdsPlan(
        actions=[
            AdsAction(kind="pause", campaign_id="abc123", reason="bajo ROAS")
        ],
        summary="Pausar campaña de bajo rendimiento",
        expected_impact="Ahorro del 15% del presupuesto",
    )

    with patch(
        "bot_estiv.graph.meta_ads_manager.plan_changes", new=AsyncMock(return_value=fake_plan)
    ):
        state: State = {
            "user_text": "pausá la campaña de pérgolas",
            "user_wa_id": "",
            "messages": [],
        }
        result = await node_ads(state)

    assert "Meta Ads" in result["reply_text"]
    assert result["ads_plan"]["summary"] == "Pausar campaña de bajo rendimiento"
