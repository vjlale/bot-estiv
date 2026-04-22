"""Tests del Brand Guardian reforzado: contraste, legibilidad, logo."""
from __future__ import annotations

import io

from PIL import Image

from bot_estiv.agents import brand_guardian


def _img_filled(w: int, h: int, color: str) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_wcag_contrast_black_on_white():
    ratio = brand_guardian.wcag_contrast((0, 0, 0), (255, 255, 255))
    assert 20 <= ratio <= 22  # max teórico ~21:1


def test_wcag_contrast_low():
    ratio = brand_guardian.wcag_contrast((180, 180, 180), (200, 200, 200))
    assert ratio < 1.5


def test_validate_image_contrast_fails_for_low():
    # imagen blanca como fondo, título blanco → contraste 1:1 → issue
    png = _img_filled(1080, 1350, "#FFFFFF")
    result = brand_guardian.validate_image(
        png,
        fmt_key="ig_feed_portrait",
        expected_title_bbox=(60, 900, 1020, 1100),
        expected_title_color="#FFFFFF",
        logo_bbox=(900, 1240, 1020, 1310),
    )
    assert result.passed is False
    assert any("Contraste del título" in i for i in result.issues)


def test_validate_image_contrast_ok_dark_bg():
    # fondo oscuro, título claro → contraste alto
    png = _img_filled(1080, 1350, "#111111")
    result = brand_guardian.validate_image(
        png,
        fmt_key="ig_feed_portrait",
        expected_title_bbox=(60, 900, 1020, 1100),
        expected_title_color="#F5F1EA",
    )
    # con sólo warnings de paleta es aceptable; critical issue no debe haber
    assert not any("Contraste" in i for i in result.issues)


def test_validate_image_wrong_size_fails():
    png = _img_filled(800, 600, "#333333")
    result = brand_guardian.validate_image(png, fmt_key="ig_feed_portrait")
    assert result.passed is False
    assert any("Tamaño" in i for i in result.issues)


def test_validate_image_logo_all_white_warns():
    # imagen casi blanca → zona del logo blanca → issue
    png = _img_filled(1080, 1350, "#FEFEFE")
    result = brand_guardian.validate_image(
        png,
        fmt_key="ig_feed_portrait",
        logo_bbox=(900, 1240, 1020, 1310),
    )
    assert any("logo" in i.lower() for i in result.issues)


def test_validate_rendered_template_runs():
    """End-to-end con la plantilla editorial_hero BUILTIN + imagen oscura."""
    png = _img_filled(1080, 1350, "#222222")
    result = brand_guardian.validate_rendered_template(
        png, template_name="editorial_hero", fmt_key="ig_feed_portrait"
    )
    # no crash, devuelve BrandCheckResult
    assert hasattr(result, "score")
    assert 0.0 <= result.score <= 1.0
