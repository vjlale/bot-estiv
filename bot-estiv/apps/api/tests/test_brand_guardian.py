"""Tests de BrandGuardian."""
from bot_estiv.agents import brand_guardian
from bot_estiv.schemas import CopyDraft


def test_forbidden_tokens_block_caption():
    copy = CopyDraft(
        title="Pérgola de Quebracho",
        caption="¡Oferta increíble! ¡Aprovechá antes que se acabe!",
        hashtags=["#GardensWood", "#Pergolas"] * 5,
        cta="visitá el showroom",
    )
    result = brand_guardian.validate_copy(copy)
    assert not result.passed
    assert any("prohibidos" in i for i in result.issues)


def test_valid_caption_passes():
    copy = CopyDraft(
        title="La nobleza del Quebracho",
        caption=(
            "Creamos el espacio de encuentro que soñaste. "
            "Artesanía que se siente en cada detalle. "
            "Diseñado para perdurar generaciones."
        ),
        hashtags=[
            "#GardensWood", "#DisenadoParaDurar", "#QuebrachoArgentino",
            "#Paisajismo", "#DisenoExterior", "#MueblesDeJardin",
            "#Pergolas", "#Decks", "#Fogoneros",
        ],
        cta="Visitá el showroom",
    )
    result = brand_guardian.validate_copy(copy)
    assert result.passed, result.issues
    assert result.score > 0.9


def test_too_few_hashtags_warns():
    copy = CopyDraft(
        title="Deck de Quebracho",
        caption="La nobleza del Quebracho en su máxima expresión.",
        hashtags=["#GardensWood"],
        cta=None,
    )
    result = brand_guardian.validate_copy(copy)
    assert not result.passed
    assert any("Muy pocos" in i for i in result.issues)
