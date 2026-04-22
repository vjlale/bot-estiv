"""Tests del Director (solo parte regex de approval)."""
from bot_estiv.agents import director


def test_approval_regex():
    d = director.classify("APROBAR 11111111-1111-1111-1111-111111111111")
    assert d.intent == "approval_decision"
    assert d.decision == "aprobar"
    assert d.post_id == "11111111-1111-1111-1111-111111111111"


def test_edit_with_reason():
    d = director.classify(
        "EDITAR 22222222-2222-2222-2222-222222222222 sacá el logo del costado izquierdo"
    )
    assert d.intent == "approval_decision"
    assert d.decision == "editar"
    assert "logo" in (d.reason or "")
