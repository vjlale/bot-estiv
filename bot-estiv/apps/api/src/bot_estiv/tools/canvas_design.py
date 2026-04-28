"""Composición final de piezas: redimensionado a tamaños exactos,
overlay de logo, safe zones y tipografías de marca.

Se complementa con la skill local `canvas-design` (manual de diseño);
esta función aplica las reglas mecánicas que toda pieza debe respetar:
- Canvas exacto del formato solicitado (1080x1350, 1080x1920, etc.)
- Logo en esquina inferior derecha con margen = 4% del lado corto
- Safe zones: 10% top/bottom para stories (evita UI de IG)
- Paleta y tipografías del manual (Playfair Display + Montserrat)
"""
from __future__ import annotations

import io
import logging
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..brand import FORMATS, PALETTE, TYPOGRAPHY
from ..config import settings

logger = logging.getLogger(__name__)


def _brand_dir(kind: str, env_name: str) -> Path:
    env_path = os.getenv(env_name)
    candidates = [Path(env_path)] if env_path else []
    here = Path(__file__).resolve()
    candidates.append(Path("/app/packages/brand") / kind)
    candidates.extend(parent / "packages" / "brand" / kind for parent in here.parents)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else Path("packages") / "brand" / kind


_FONTS_DIR = _brand_dir("fonts", "BRAND_FONTS_DIR")


def _load_logo() -> Image.Image | None:
    p = settings.brand_logo_abs
    if not p.exists():
        logger.warning("brand_logo.missing", extra={"path": str(p)})
        return None
    return Image.open(p).convert("RGBA")


@lru_cache(maxsize=32)
def _load_font(kind: str = "heading", size: int = 64) -> ImageFont.FreeTypeFont:
    """Carga fuentes reales de marca (Playfair Display + Montserrat) desde
    `packages/brand/fonts/`. Si falla cae a DejaVu y luego al default de Pillow.

    `kind` admite: heading | heading_bold | body | body_medium | body_semibold | body_bold
    """
    by_kind: dict[str, list[str]] = {
        "heading": ["PlayfairDisplay-Regular.ttf"],
        "heading_bold": ["PlayfairDisplay-Bold.ttf", "PlayfairDisplay-Regular.ttf"],
        "body": ["Montserrat-Regular.ttf"],
        "body_medium": ["Montserrat-Medium.ttf", "Montserrat-Regular.ttf"],
        "body_semibold": ["Montserrat-SemiBold.ttf", "Montserrat-Medium.ttf"],
        "body_bold": ["Montserrat-Bold.ttf", "Montserrat-SemiBold.ttf"],
    }
    candidates = by_kind.get(kind, by_kind["heading"])
    for name in candidates:
        path = _FONTS_DIR / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError as exc:
                logger.warning("font.load_failed", extra={"path": str(path), "err": str(exc)})

    # Fallbacks de sistema (solo si estamos en contenedor Linux con fonts instaladas)
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in fallbacks:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    logger.warning("font.using_default", extra={"kind": kind})
    return ImageFont.load_default()


def place_logo(img: Image.Image, opacity: float = 0.9, margin_ratio: float = 0.04) -> Image.Image:
    logo = _load_logo()
    if logo is None:
        return img

    short_side = min(img.size)
    margin = int(short_side * margin_ratio)
    target_w = int(short_side * 0.18)
    ratio = target_w / logo.width
    target_h = int(logo.height * ratio)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    if opacity < 1.0:
        alpha = logo.split()[3].point(lambda a: int(a * opacity))
        logo.putalpha(alpha)

    base = img.convert("RGBA")
    x = base.width - target_w - margin
    y = base.height - target_h - margin
    base.alpha_composite(logo, (x, y))
    return base.convert("RGB")


def fit_to_format(img: Image.Image, fmt_key: str) -> Image.Image:
    """Crop/resize cover a las dimensiones exactas del formato."""
    w, h = FORMATS[fmt_key]
    return _cover_resize(img, w, h)


def _cover_resize(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_ratio = img.width / img.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_h = target_h
        new_w = int(target_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(target_w / src_ratio)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def add_headline_overlay(
    img: Image.Image,
    headline: str,
    subtitle: str | None = None,
    position: str = "bottom",
    palette_bg: str = PALETTE.gris_carbon,
    palette_fg: str = PALETTE.blanco_hueso,
) -> Image.Image:
    """Agrega una franja elegante con título Playfair + bajada Montserrat."""
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    W, H = base.size
    band_h = int(H * 0.26)
    y0 = H - band_h if position == "bottom" else 0
    y1 = y0 + band_h

    r, g, b = tuple(int(palette_bg[i : i + 2], 16) for i in (1, 3, 5))
    draw.rectangle([(0, y0), (W, y1)], fill=(r, g, b, 215))

    heading_font = _load_font("heading", int(H * 0.055))
    body_font = _load_font("body", int(H * 0.028))

    pad_x = int(W * 0.06)
    draw.text(
        (pad_x, y0 + int(band_h * 0.22)),
        headline,
        fill=palette_fg,
        font=heading_font,
    )
    if subtitle:
        draw.text(
            (pad_x, y0 + int(band_h * 0.62)),
            subtitle,
            fill=palette_fg,
            font=body_font,
        )

    base.alpha_composite(overlay)
    return base.convert("RGB")


def finalize(
    raw_png: bytes,
    fmt_key: str,
    headline: str | None = None,
    subtitle: str | None = None,
    add_logo: bool = True,
) -> bytes:
    """Pipeline completo: crop al formato → overlay opcional → logo → PNG."""
    img = Image.open(io.BytesIO(raw_png)).convert("RGB")
    img = fit_to_format(img, fmt_key)
    if headline:
        img = add_headline_overlay(img, headline, subtitle)
    if add_logo:
        img = place_logo(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def quick_brand_card(
    text: str,
    fmt_key: str = "ig_feed_square",
    bg: str = PALETTE.blanco_hueso,
    fg: str = PALETTE.gris_carbon,
) -> bytes:
    """Tarjeta puramente tipográfica en paleta de marca (placeholder/fallback)."""
    w, h = FORMATS[fmt_key]
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    font = _load_font("heading", int(h * 0.08))
    lines = _wrap(text, font, int(w * 0.85), draw)
    total_h = sum(draw.textbbox((0, 0), ln, font=font)[3] for ln in lines)
    y = (h - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill=fg, font=font)
        y += bbox[3] - bbox[1] + int(h * 0.02)
    img = place_logo(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
