"""Tests de tools/template_renderer.py — motor de diseño de plantillas."""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from PIL import Image

from bot_estiv.tools.template_renderer import (
    _hex_to_rgba,
    _scale_spec,
    load_template,
    list_templates,
    render,
    _BUILTIN,
)


def _solid_image(w: int = 1080, h: int = 1350) -> Image.Image:
    return Image.new("RGB", (w, h), "#3A4A5C")


# ---------------------------------------------------------------------------
# _hex_to_rgba — conversión pura de color
# ---------------------------------------------------------------------------

def test_hex_to_rgba_black():
    assert _hex_to_rgba("#000000") == (0, 0, 0, 255)


def test_hex_to_rgba_white():
    assert _hex_to_rgba("#FFFFFF") == (255, 255, 255, 255)


def test_hex_to_rgba_brand_carbon():
    r, g, b, a = _hex_to_rgba("#36454F")
    assert r == 0x36
    assert g == 0x45
    assert b == 0x4F
    assert a == 255


def test_hex_to_rgba_with_opacity():
    r, g, b, a = _hex_to_rgba("#FFFFFF", alpha=0.5)
    assert a == 127  # int(0.5 * 255)


def test_hex_to_rgba_without_hash_prefix():
    r, g, b, a = _hex_to_rgba("F5F1EA")
    assert r == 0xF5
    assert g == 0xF1
    assert b == 0xEA


# ---------------------------------------------------------------------------
# load_template — carga builtin o fallback
# ---------------------------------------------------------------------------

def test_load_template_editorial_hero():
    spec = load_template("editorial_hero")
    assert spec.name == "editorial_hero"
    assert "image" in spec.slots
    assert "title" in spec.slots


def test_load_template_minimal_stamp():
    spec = load_template("minimal_stamp")
    assert spec.name == "minimal_stamp"
    assert "image" in spec.slots
    assert "logo" in spec.slots


def test_load_template_cover_hero():
    spec = load_template("cover_hero")
    assert spec.name == "cover_hero"
    assert "title" in spec.slots


def test_load_template_split_60_40():
    spec = load_template("split_60_40")
    assert spec.name == "split_60_40"
    assert "image" in spec.slots
    assert "title" in spec.slots


def test_load_template_spec_card():
    spec = load_template("spec_card")
    assert spec.name == "spec_card"


def test_load_template_unknown_falls_back_to_editorial_hero():
    spec = load_template("no_existe_esta_plantilla")
    assert spec.name == "editorial_hero"


# ---------------------------------------------------------------------------
# list_templates — devuelve al menos los builtin
# ---------------------------------------------------------------------------

def test_list_templates_contains_all_builtins():
    templates = list_templates()
    for name in _BUILTIN:
        assert name in templates


def test_list_templates_sorted():
    templates = list_templates()
    assert templates == sorted(templates)


# ---------------------------------------------------------------------------
# _scale_spec — escala proporcional de bboxes
# ---------------------------------------------------------------------------

def test_scale_spec_identity_no_change():
    spec = load_template("editorial_hero")
    scaled = _scale_spec(spec, 1080, 1350)
    # mismas dimensiones: no cambia nada
    assert scaled.size == (1080, 1350)
    assert scaled.slots["title"].bbox == spec.slots["title"].bbox


def test_scale_spec_half_size():
    spec = load_template("editorial_hero")
    scaled = _scale_spec(spec, 540, 675)
    x1, y1, x2, y2 = scaled.slots["title"].bbox
    orig_x1, orig_y1, orig_x2, orig_y2 = spec.slots["title"].bbox
    assert x1 == orig_x1 // 2
    assert y1 == orig_y1 // 2


# ---------------------------------------------------------------------------
# render — produce PNG bytes con imagen real
# ---------------------------------------------------------------------------

def test_render_editorial_hero_returns_png():
    img = _solid_image()
    with patch("bot_estiv.tools.template_renderer._draw_logo_slot"):
        with patch("bot_estiv.tools.template_renderer._load_font") as mock_font:
            from PIL import ImageFont

            mock_font.return_value = ImageFont.load_default()
            result = render(
                "editorial_hero",
                {"image": img, "title": "Diseñado para Durar", "subtitle": "Quebracho puro"},
            )
    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_render_minimal_stamp_no_title():
    img = _solid_image()
    with patch("bot_estiv.tools.template_renderer._draw_logo_slot"):
        result = render("minimal_stamp", {"image": img, "pillar_tag": "DURABILIDAD"})
    assert isinstance(result, bytes)


def test_render_cover_hero_with_target_size():
    img = _solid_image(1080, 1920)
    with patch("bot_estiv.tools.template_renderer._draw_logo_slot"):
        with patch("bot_estiv.tools.template_renderer._load_font") as mock_font:
            from PIL import ImageFont

            mock_font.return_value = ImageFont.load_default()
            result = render(
                "cover_hero",
                {"image": img, "title": "Pergolados"},
                target_size=(1080, 1920),
            )
    parsed = Image.open(io.BytesIO(result))
    assert parsed.size == (1080, 1920)


def test_render_image_as_bytes():
    img = _solid_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw = buf.getvalue()

    with patch("bot_estiv.tools.template_renderer._draw_logo_slot"):
        result = render("minimal_stamp", {"image": raw})
    assert isinstance(result, bytes)


def test_render_no_image_still_produces_output():
    with patch("bot_estiv.tools.template_renderer._draw_logo_slot"):
        with patch("bot_estiv.tools.template_renderer._load_font") as mock_font:
            from PIL import ImageFont

            mock_font.return_value = ImageFont.load_default()
            result = render("editorial_hero", {"image": None, "title": "Sin imagen"})
    assert isinstance(result, bytes)


def test_render_spec_object_directly():
    spec = load_template("spec_card")
    img = _solid_image()
    with patch("bot_estiv.tools.template_renderer._draw_logo_slot"):
        result = render(spec, {"image": img})
    assert isinstance(result, bytes)
