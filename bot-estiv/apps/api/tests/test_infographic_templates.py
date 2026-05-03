"""Tests de las plantillas infográficas nuevas: infographic_dimensions y numbered_steps."""
from __future__ import annotations

import io

from PIL import Image

from bot_estiv.tools import template_renderer as tr


def _dummy_product(w: int = 1200, h: int = 600) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # rect marrón que simula producto
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.rectangle([(100, 200), (w - 100, h - 100)], fill=(100, 60, 30, 255))
    return img


def test_dimensions_template_exists_and_has_slots():
    spec = tr.load_template("infographic_dimensions")
    assert spec.name == "infographic_dimensions"
    assert "image" in spec.slots
    assert "title" in spec.slots
    assert "dim_top_label" in spec.slots
    assert "dim_right_label" in spec.slots
    assert "description_body" in spec.slots
    assert "logo" in spec.slots
    assert spec.background_color == "#F5F1EA"
    assert spec.size == (1920, 1080)


def test_numbered_steps_template_exists_and_has_step_slots():
    spec = tr.load_template("numbered_steps")
    assert spec.name == "numbered_steps"
    for i in (1, 2, 3):
        assert f"step_{i}_title" in spec.slots
        assert f"step_{i}_body" in spec.slots
    # 3 numbered_badges
    badges = [d for d in spec.decorations if d.type == "numbered_badge"]
    assert len(badges) == 3
    assert [b.number for b in badges] == [1, 2, 3]


def test_dimensions_template_renders_png():
    values = {
        "image": _dummy_product(1200, 600),
        "title": "Dimensiones concebidas",
        "dim_top_label": "2,20 m",
        "dim_right_label": "76 cm",
        "description_title": "UNA PIEZA CONSTRUCTIVA",
        "description_body": "Descripción larga para validar wrap y render.",
    }
    png = tr.render(spec="infographic_dimensions", values=values, target_size=(1920, 1080))
    img = Image.open(io.BytesIO(png)).convert("RGB")
    assert img.size == (1920, 1080)
    # el fondo en (10,10) debe ser cercano al hueso #F5F1EA
    r, g, b = img.getpixel((10, 10))
    assert 230 < r < 255 and 225 < g < 250


def test_numbered_steps_template_renders_png():
    values = {
        "image": _dummy_product(500, 700),
        "title": "Ingeniería Oculta",
        "step_1_title": "Fijación",
        "step_1_body": "Cada durmiente se entierra 20-30 cm bajo el suelo.",
        "step_2_title": "Continuo",
        "step_2_body": "Sin fisuras entre postes.",
        "step_3_title": "Hormigonado",
        "step_3_body": "Anclaje individual resistente a vientos.",
    }
    png = tr.render(spec="numbered_steps", values=values, target_size=(1920, 1080))
    img = Image.open(io.BytesIO(png)).convert("RGB")
    assert img.size == (1920, 1080)


def test_infographic_templates_scale_to_smaller_canvas():
    """El renderer debe escalar proporcionalmente a otros formatos."""
    values = {"image": _dummy_product(800, 400), "title": "x"}
    png = tr.render(spec="infographic_dimensions", values=values, target_size=(1200, 675))
    img = Image.open(io.BytesIO(png)).convert("RGB")
    assert img.size == (1200, 675)


def test_all_builtin_templates_listed():
    names = tr.list_templates()
    for required in (
        "editorial_hero",
        "minimal_stamp",
        "cover_hero",
        "split_60_40",
        "spec_card",
        "infographic_dimensions",
        "numbered_steps",
    ):
        assert required in names, f"missing template: {required}"
