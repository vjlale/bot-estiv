"""Tests del PhotoEditor: color grading + auto crop + pick cover."""
from __future__ import annotations

from PIL import Image

from bot_estiv.tools import photo_editor


def _gradient(w: int, h: int, start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (w, h), start)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(start[0] + (end[0] - start[0]) * t)
        g = int(start[1] + (end[1] - start[1]) * t)
        b = int(start[2] + (end[2] - start[2]) * t)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img


def test_color_grade_preserves_size_and_mode():
    img = Image.new("RGB", (320, 480), (120, 100, 80))
    out = photo_editor.color_grade_gw(img)
    assert out.size == img.size
    assert out.mode == "RGB"


def test_color_grade_warms_shadows():
    """Un pixel oscuro (gris) debe volverse más cálido (más R, menos B)."""
    img = Image.new("RGB", (4, 4), (40, 40, 40))
    out = photo_editor.color_grade_gw(img, strength=1.0)
    r, g, b = out.getpixel((0, 0))
    assert r > 40
    assert b < 40


def test_auto_crop_returns_exact_format():
    # fuente 1600x900 (horizontal) → recorte portrait 1080x1350
    img = Image.new("RGB", (1600, 900), (100, 90, 60))
    out = photo_editor.auto_crop(img, "ig_feed_portrait")
    assert out.size == (1080, 1350)


def test_auto_crop_square_to_portrait():
    img = Image.new("RGB", (1000, 1000), (80, 80, 80))
    out = photo_editor.auto_crop(img, "ig_feed_portrait")
    assert out.size == (1080, 1350)


def test_pick_cover_selects_sharpest():
    # imagen difusa vs con edges
    blur = Image.new("RGB", (800, 1000), (90, 90, 90))
    sharp = Image.new("RGB", (800, 1000), (90, 90, 90))
    # agregar edges a sharp
    for x in range(0, 800, 20):
        for y in range(1000):
            sharp.putpixel((x, y), (220, 220, 220))
    best = photo_editor.pick_cover([blur, sharp], fmt_key="ig_feed_portrait")
    assert best.index == 1


def test_process_photo_pipeline_full():
    img = Image.new("RGB", (1920, 1080), (150, 120, 80))
    png = photo_editor.process_photo(img, fmt_key="ig_feed_portrait")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"

    from PIL import Image as PILImage
    import io
    decoded = PILImage.open(io.BytesIO(png))
    assert decoded.size == (1080, 1350)
