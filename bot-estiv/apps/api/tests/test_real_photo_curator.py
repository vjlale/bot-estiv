"""Tests del RealPhotoCurator: asignación de roles narrativos."""
from __future__ import annotations

from PIL import Image

from bot_estiv.agents import real_photo_curator


def _solid(w: int, h: int, color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (w, h), color)


def _edges(w: int, h: int) -> Image.Image:
    """Imagen con mucha textura (sharpness alta)."""
    img = Image.new("RGB", (w, h), (100, 100, 100))
    for x in range(0, w, 4):
        for y in range(h):
            img.putpixel((x, y), (220, 220, 220))
    return img


def test_curate_assigns_four_roles():
    photos = [
        _solid(1000, 1200, (80, 60, 40)),   # plano uniforme
        _edges(1000, 1200),                  # con textura
        _solid(1000, 1200, (90, 85, 60)),    # plano
        _solid(1200, 800, (110, 100, 80)),   # horizontal
    ]
    curated, slides = real_photo_curator.curate_to_slides(
        photos, topic="test obra", n_slides=4, fmt_key="ig_feed_portrait"
    )
    assert len(curated.order) == 4
    assert len(slides) == 4
    roles = [cp.role for cp in curated.order]
    assert "apertura" in roles
    assert "detalle" in roles


def test_curate_with_three_photos_gives_three_slides():
    photos = [_solid(1080, 1350, (80, 80, 80)) for _ in range(3)]
    curated, slides = real_photo_curator.curate_to_slides(
        photos, topic="test obra", n_slides=5, fmt_key="ig_feed_portrait"
    )
    assert len(curated.order) == 3
    assert len(slides) == 3


def test_template_assigned_from_role():
    photos = [_solid(1080, 1350, (80, 80, 80)) for _ in range(4)]
    curated, slides = real_photo_curator.curate_to_slides(photos, "test", n_slides=4)
    role_to_template = {cp.role: cp.template for cp in curated.order}
    assert role_to_template.get("apertura") == "cover_hero"
    assert role_to_template.get("detalle") == "minimal_stamp"
