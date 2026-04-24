"""Tests de los routers de la API usando FastAPI TestClient con DB mockeada."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot_estiv.models import Post, PostFormat, PostStatus, Approval


# ---------------------------------------------------------------------------
# /health + /
# ---------------------------------------------------------------------------

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "service" in data


async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "Bot Estiv" in r.json()["name"]


# ---------------------------------------------------------------------------
# /posts
# ---------------------------------------------------------------------------

async def test_list_posts_empty(client):
    r = await client.get("/posts")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_posts_with_results(app, client):
    from bot_estiv.db import get_session

    fake_post = MagicMock(spec=Post)
    fake_post.id = uuid.uuid4()
    fake_post.title = "Pérgolas de Quebracho"
    fake_post.caption = "La nobleza del Quebracho..."
    fake_post.hashtags = ["#GardensWood"]
    fake_post.format = PostFormat.IG_FEED_PORTRAIT
    fake_post.status = PostStatus.PENDING_APPROVAL
    fake_post.pillar = "durabilidad"
    fake_post.scheduled_for = None
    fake_post.published_at = None
    fake_post.assets = []
    fake_post.created_at = "2024-01-01T00:00:00"

    async def override():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [fake_post]
        session.execute.return_value = result
        yield session

    app.dependency_overrides[get_session] = override
    r = await client.get("/posts")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "Pérgolas de Quebracho"


async def test_list_posts_with_status_filter(client):
    r = await client.get("/posts?status=pending_approval")
    assert r.status_code == 200


async def test_list_posts_limit_respected(client):
    r = await client.get("/posts?limit=10")
    assert r.status_code == 200


async def test_get_post_not_found(client):
    r = await client.get(f"/posts/{uuid.uuid4()}")
    assert r.status_code == 404
    assert "no encontrado" in r.json()["detail"].lower()


async def test_get_post_found(app, client):
    from bot_estiv.db import get_session

    post_id = uuid.uuid4()
    fake_post = MagicMock(spec=Post)
    fake_post.id = post_id
    fake_post.title = "Test post"
    fake_post.caption = "Test caption"
    fake_post.hashtags = []
    fake_post.format = PostFormat.IG_FEED_PORTRAIT
    fake_post.status = PostStatus.DRAFT
    fake_post.pillar = None
    fake_post.scheduled_for = None
    fake_post.published_at = None
    fake_post.assets = []
    fake_post.created_at = "2024-01-01T00:00:00"

    async def override():
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = fake_post
        session.execute.return_value = result
        yield session

    app.dependency_overrides[get_session] = override
    r = await client.get(f"/posts/{post_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Test post"


# ---------------------------------------------------------------------------
# /approvals
# ---------------------------------------------------------------------------

async def test_list_approvals_empty(client):
    r = await client.get("/approvals")
    assert r.status_code == 200
    assert r.json() == []


async def test_decide_approval_not_found(client):
    r = await client.post(
        f"/approvals/{uuid.uuid4()}/decision",
        json={"decision": "approve"},
    )
    assert r.status_code == 404


def _make_approval_session(fake_approval, fake_post):
    """Crea una AsyncSession mockeada que devuelve fake_approval o fake_post
    según la tabla que el stmt consulte, sin depender del orden de las llamadas."""
    session = AsyncMock()

    def side_effect(stmt):
        result = MagicMock()
        try:
            table_name = stmt.get_final_froms()[0].name
        except (AttributeError, IndexError):
            table_name = ""
        if table_name == "approvals":
            result.scalar_one_or_none.return_value = fake_approval
            result.scalar_one.return_value = fake_approval
        else:
            result.scalar_one_or_none.return_value = fake_post
            result.scalar_one.return_value = fake_post
        return result

    session.execute = AsyncMock(side_effect=side_effect)
    session.commit = AsyncMock()
    return session


async def test_decide_approval_approve(app, client):
    from bot_estiv.db import get_session

    post_id = uuid.uuid4()
    fake_approval = MagicMock(spec=Approval)
    fake_approval.id = uuid.uuid4()
    fake_approval.post_id = post_id
    fake_approval.status = "pending"
    fake_approval.requested_at = "2024-01-01T00:00:00"
    fake_approval.decided_at = None

    fake_post = MagicMock(spec=Post)
    fake_post.id = post_id
    fake_post.status = PostStatus.PENDING_APPROVAL

    async def override():
        yield _make_approval_session(fake_approval, fake_post)

    app.dependency_overrides[get_session] = override
    r = await client.post(
        f"/approvals/{post_id}/decision",
        json={"decision": "approve", "reason": None},
    )
    assert r.status_code == 200
    assert fake_approval.status == "approved"


async def test_decide_approval_reject(app, client):
    from bot_estiv.db import get_session

    post_id = uuid.uuid4()
    fake_approval = MagicMock(spec=Approval)
    fake_approval.id = uuid.uuid4()
    fake_approval.post_id = post_id
    fake_approval.status = "pending"
    fake_approval.requested_at = "2024-01-01T00:00:00"
    fake_approval.decided_at = None

    fake_post = MagicMock(spec=Post)
    fake_post.id = post_id
    fake_post.status = PostStatus.PENDING_APPROVAL

    async def override():
        yield _make_approval_session(fake_approval, fake_post)

    app.dependency_overrides[get_session] = override
    r = await client.post(
        f"/approvals/{post_id}/decision",
        json={"decision": "reject", "reason": "No cumple con la marca"},
    )
    assert r.status_code == 200
    assert fake_approval.status == "rejected"
    assert fake_post.status == PostStatus.REJECTED


async def test_decide_approval_edit(app, client):
    from bot_estiv.db import get_session

    post_id = uuid.uuid4()
    fake_approval = MagicMock(spec=Approval)
    fake_approval.id = uuid.uuid4()
    fake_approval.post_id = post_id
    fake_approval.status = "pending"
    fake_approval.requested_at = "2024-01-01T00:00:00"
    fake_approval.decided_at = None

    fake_post = MagicMock(spec=Post)
    fake_post.id = post_id
    fake_post.status = PostStatus.PENDING_APPROVAL

    async def override():
        yield _make_approval_session(fake_approval, fake_post)

    app.dependency_overrides[get_session] = override
    r = await client.post(
        f"/approvals/{post_id}/decision",
        json={"decision": "edit", "reason": "Cambiar el tono"},
    )
    assert r.status_code == 200
    assert fake_approval.status == "edit_requested"
    assert fake_post.status == PostStatus.DRAFT


# ---------------------------------------------------------------------------
# /campaigns
# ---------------------------------------------------------------------------

async def test_list_campaigns_502_when_meta_fails(client):
    with patch("bot_estiv.routers.campaigns.meta_ads.list_campaigns", side_effect=Exception("no creds")):
        r = await client.get("/campaigns")
    assert r.status_code == 502


async def test_list_campaigns_success(client):
    fake_campaigns = [{"id": "123", "name": "GW_Verano", "status": "PAUSED"}]
    with patch("bot_estiv.routers.campaigns.meta_ads.list_campaigns", return_value=fake_campaigns):
        r = await client.get("/campaigns")
    assert r.status_code == 200
    assert r.json()[0]["name"] == "GW_Verano"


async def test_plan_campaigns(client):
    from bot_estiv.agents.meta_ads_manager import AdsPlan, AdsAction

    fake_plan = AdsPlan(
        actions=[
            AdsAction(
                kind="create",
                name="GW_Pérgolas_2024",
                objective="OUTCOME_TRAFFIC",
                daily_budget_cents=50000,
                reason="Temporada primavera",
            )
        ],
        summary="Crear campaña de pérgolas para primavera",
        expected_impact="Aumento de 20% en consultas",
    )
    with patch("bot_estiv.routers.campaigns.plan_changes", new=AsyncMock(return_value=fake_plan)):
        r = await client.post("/campaigns/plan?instruction=crear campaña")
    assert r.status_code == 200
    assert r.json()["summary"] == "Crear campaña de pérgolas para primavera"


async def test_apply_campaign_action_502(client):
    from bot_estiv.agents.meta_ads_manager import AdsAction

    action = AdsAction(kind="pause", campaign_id="123", reason="bajo ROAS")
    with patch("bot_estiv.routers.campaigns.apply_action", side_effect=Exception("API error")):
        r = await client.post("/campaigns/apply", json=action.model_dump())
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# /webhook/twilio
# ---------------------------------------------------------------------------

async def test_webhook_missing_from_returns_400(client):
    r = await client.post("/webhook/twilio", data={})
    assert r.status_code == 400


async def test_webhook_valid_returns_twiml(client):
    form_data = {
        "From": "whatsapp:+5491112345678",
        "Body": "Hola",
        "NumMedia": "0",
        "MessageSid": "SM123",
        "To": "whatsapp:+15005550006",
    }
    with patch("bot_estiv.routers.webhook._handle", new=AsyncMock()):
        r = await client.post(
            "/webhook/twilio",
            content="&".join(f"{k}={v}" for k, v in form_data.items()),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    assert r.status_code == 200
    assert "Response" in r.text
