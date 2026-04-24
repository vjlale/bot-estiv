"""Tests de tools/canvas_design.py — funciones puras de composición de imágenes."""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from PIL import Image

from bot_estiv.tools.canvas_design import (
    _cover_resize,
    _wrap,
    add_headline_overlay,
    fit_to_format,
    finalize,
    quick_brand_card,
    place_logo,
)


def _solid_image(w: int = 400, h: int = 300, color: str = "red") -> Image.Image:
    return Image.new("RGB", (w, h), color)


# ---------------------------------------------------------------------------
# _cover_resize — función pura de redimensionado
# ---------------------------------------------------------------------------

def test_cover_resize_to_exact_size():
    img = _solid_image(800, 600)
    result = _cover_resize(img, 400, 400)
    assert result.size == (400, 400)


def test_cover_resize_wide_source_to_portrait():
    img = _solid_image(1600, 400)  # muy ancha
    result = _cover_resize(img, 1080, 1350)
    assert result.size == (1080, 1350)


def test_cover_resize_portrait_source_to_square():
    img = _solid_image(400, 800)  # portrait
    result = _cover_resize(img, 500, 500)
    assert result.size == (500, 500)


def test_cover_resize_same_ratio_no_distortion():
    img = _solid_image(1080, 1350)
    result = _cover_resize(img, 1080, 1350)
    assert result.size == (1080, 1350)


# ---------------------------------------------------------------------------
# fit_to_format — usa FORMATS dict
# ---------------------------------------------------------------------------

def test_fit_to_format_ig_feed_portrait():
    img = _solid_image(500, 500)
    result = fit_to_format(img, "ig_feed_portrait")
    assert result.size == (1080, 1350)


def test_fit_to_format_ig_story():
    img = _solid_image(500, 500)
    result = fit_to_format(img, "ig_story")
    assert result.size == (1080, 1920)


def test_fit_to_format_carousel_portrait():
    img = _solid_image(500, 500)
    result = fit_to_format(img, "carousel_portrait")
    assert result.size == (1080, 1350)


# ---------------------------------------------------------------------------
# add_headline_overlay — aplica texto sobre imagen
# ---------------------------------------------------------------------------

def test_add_headline_overlay_returns_correct_size():
    img = _solid_image(1080, 1350)
    with patch("bot_estiv.tools.canvas_design._load_font") as mock_font:
        from PIL import ImageFont

        mock_font.return_value = ImageFont.load_default()
        result = add_headline_overlay(img, "Diseñado para Durar")
    assert result.size == (1080, 1350)
    assert result.mode == "RGB"


def test_add_headline_overlay_with_subtitle():
    img = _solid_image(1080, 1350)
    with patch("bot_estiv.tools.canvas_design._load_font") as mock_font:
        from PIL import ImageFont

        mock_font.return_value = ImageFont.load_default()
        result = add_headline_overlay(img, "Título principal", subtitle="Bajada del texto")
    assert result.size == (1080, 1350)


# ---------------------------------------------------------------------------
# place_logo — no falla si no hay logo
# ---------------------------------------------------------------------------

def test_place_logo_without_logo_returns_original():
    img = _solid_image(1080, 1350)
    with patch("bot_estiv.tools.canvas_design._load_logo", return_value=None):
        result = place_logo(img)
    assert result.size == img.size


def test_place_logo_with_logo_composites():
    img = _solid_image(1080, 1350)
    logo = Image.new("RGBA", (200, 100), (255, 255, 255, 200))
    with patch("bot_estiv.tools.canvas_design._load_logo", return_value=logo):
        result = place_logo(img)
    assert result.mode == "RGB"
    assert result.size == img.size


# ---------------------------------------------------------------------------
# finalize — pipeline completo: resize → overlay → logo → PNG bytes
# ---------------------------------------------------------------------------

def test_finalize_returns_png_bytes():
    img = _solid_image(800, 600)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_png = buf.getvalue()

    with patch("bot_estiv.tools.canvas_design._load_logo", return_value=None):
        result = finalize(raw_png, "ig_feed_portrait")

    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_finalize_with_headline():
    img = _solid_image(800, 600)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_png = buf.getvalue()

    with (
        patch("bot_estiv.tools.canvas_design._load_logo", return_value=None),
        patch("bot_estiv.tools.canvas_design._load_font") as mock_font,
    ):
        from PIL import ImageFont

        mock_font.return_value = ImageFont.load_default()
        result = finalize(raw_png, "ig_story", headline="Artesanía en Quebracho")

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_finalize_without_logo_flag():
    img = _solid_image(800, 600)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_png = buf.getvalue()

    result = finalize(raw_png, "ig_feed_portrait", add_logo=False)
    assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# quick_brand_card — tarjeta tipográfica de fallback
# ---------------------------------------------------------------------------

def test_quick_brand_card_returns_png_bytes():
    with patch("bot_estiv.tools.canvas_design._load_logo", return_value=None):
        with patch("bot_estiv.tools.canvas_design._load_font") as mock_font:
            from PIL import ImageFont

            mock_font.return_value = ImageFont.load_default()
            result = quick_brand_card("Gardens Wood")

    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_quick_brand_card_uses_correct_format():
    with patch("bot_estiv.tools.canvas_design._load_logo", return_value=None):
        with patch("bot_estiv.tools.canvas_design._load_font") as mock_font:
            from PIL import ImageFont

            mock_font.return_value = ImageFont.load_default()
            result = quick_brand_card("Texto corto", fmt_key="ig_feed_square")

    parsed = Image.open(io.BytesIO(result))
    assert parsed.size == (1080, 1080)


# ---------------------------------------------------------------------------
# _wrap — text wrapping puro
# ---------------------------------------------------------------------------

def test_wrap_single_word():
    from PIL import ImageFont, ImageDraw

    img = Image.new("RGB", (400, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    lines = _wrap("palabra", font, 400, draw)
    assert lines == ["palabra"]


def test_wrap_splits_long_text():
    from PIL import ImageFont, ImageDraw

    img = Image.new("RGB", (100, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    # texto largo debería generar múltiples líneas con ancho pequeño
    lines = _wrap("uno dos tres cuatro cinco seis siete ocho nueve diez", font, 60, draw)
    assert len(lines) > 1


def test_wrap_empty_text_returns_empty():
    from PIL import ImageFont, ImageDraw

    img = Image.new("RGB", (400, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    lines = _wrap("", font, 400, draw)
    assert lines == []
