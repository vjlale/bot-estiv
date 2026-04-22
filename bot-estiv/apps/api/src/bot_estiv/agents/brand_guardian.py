"""BrandGuardian: valida que el output cumpla el manual de marca.

Checks mecánicos + validación semántica vía LLM.
"""
from __future__ import annotations

import io
import logging
import re
from collections import Counter
from typing import Iterable

from PIL import Image

from ..brand import FORMATS, PALETTE, VOICE
from ..schemas import BrandCheckResult, CopyDraft

logger = logging.getLogger(__name__)


def _check_forbidden_tokens(text: str) -> list[str]:
    low = text.lower()
    return [tok for tok in VOICE.forbidden_tokens if tok in low]


def _check_hashtags(hashtags: list[str]) -> list[str]:
    issues: list[str] = []
    if len(hashtags) < 8:
        issues.append(f"Muy pocos hashtags ({len(hashtags)}). Mínimo 8.")
    if len(hashtags) > 30:
        issues.append(f"Demasiados hashtags ({len(hashtags)}). Máximo 30 por IG.")
    for h in hashtags:
        if not h.startswith("#"):
            issues.append(f"Hashtag sin #: {h!r}")
    return issues


def validate_copy(copy: CopyDraft) -> BrandCheckResult:
    issues: list[str] = []
    warnings: list[str] = []

    forbidden_in_caption = _check_forbidden_tokens(copy.caption)
    forbidden_in_title = _check_forbidden_tokens(copy.title)
    if forbidden_in_caption:
        issues.append(f"Caption usa términos prohibidos: {forbidden_in_caption}")
    if forbidden_in_title:
        issues.append(f"Título usa términos prohibidos: {forbidden_in_title}")

    if len(copy.title) > 90:
        warnings.append(f"Título excede 90 caracteres ({len(copy.title)}).")

    issues.extend(_check_hashtags(copy.hashtags))

    if re.search(r"!!+", copy.caption):
        warnings.append("Exceso de signos de exclamación.")

    score = max(0.0, 1.0 - 0.2 * len(issues) - 0.05 * len(warnings))
    return BrandCheckResult(passed=not issues, issues=issues, warnings=warnings, score=score)


def _dominant_colors(img: Image.Image, k: int = 6) -> list[tuple[int, int, int]]:
    small = img.convert("RGB").resize((64, 64))
    counter: Counter[tuple[int, int, int]] = Counter(small.getdata())
    return [c for c, _ in counter.most_common(k)]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))


def _color_distance(a: Iterable[int], b: Iterable[int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


# ==========  Contrast / legibilidad / logo ==========


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """Luminancia relativa WCAG 2.x."""
    def chan(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def wcag_contrast(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """Ratio de contraste WCAG (>= 4.5 AA para texto normal, >= 3.0 para largo)."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _sample_region_mean(img: Image.Image, bbox: tuple[int, int, int, int]) -> tuple[int, int, int]:
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(img.width - 1, x1))
    y1 = max(0, min(img.height - 1, y1))
    x2 = max(x1 + 1, min(img.width, x2))
    y2 = max(y1 + 1, min(img.height, y2))
    crop = img.convert("RGB").crop((x1, y1, x2, y2))
    # downsample para promedio rápido
    crop.thumbnail((32, 32))
    pixels = list(crop.getdata())
    n = len(pixels)
    r = sum(p[0] for p in pixels) // n
    g = sum(p[1] for p in pixels) // n
    b = sum(p[2] for p in pixels) // n
    return (r, g, b)


def _check_logo_area(img: Image.Image, logo_bbox: tuple[int, int, int, int]) -> list[str]:
    """Verifica que la zona del logo no esté vacía (p. ej. full blanco o full negro)."""
    r, g, b = _sample_region_mean(img, logo_bbox)
    # si es todo blanco (>245) o todo negro (<10), probablemente no hay logo visible
    issues: list[str] = []
    if max(r, g, b) > 245 and min(r, g, b) > 245:
        issues.append("Zona del logo parece blanca uniforme: logo podría no ser visible.")
    if max(r, g, b) < 10:
        issues.append("Zona del logo parece negra uniforme: logo podría no ser visible.")
    return issues


def validate_image(
    png_bytes: bytes,
    fmt_key: str | None = None,
    *,
    expected_title_bbox: tuple[int, int, int, int] | None = None,
    expected_title_color: str | None = None,
    logo_bbox: tuple[int, int, int, int] | None = None,
) -> BrandCheckResult:
    """Valida formato, paleta, contraste del título y visibilidad del logo."""
    img = Image.open(io.BytesIO(png_bytes))
    issues: list[str] = []
    warnings: list[str] = []

    # Formato exacto
    if fmt_key and fmt_key in FORMATS:
        expected = FORMATS[fmt_key]
        if img.size != expected:
            issues.append(f"Tamaño {img.size} ≠ {expected} para {fmt_key}.")

    # Paleta dominante
    palette_rgb = [_hex_to_rgb(c) for c in PALETTE.all()]
    doms = _dominant_colors(img)
    close_count = 0
    for d in doms:
        min_dist = min(_color_distance(d, p) for p in palette_rgb)
        if min_dist < 90:
            close_count += 1
    if close_count < 2:
        warnings.append("Paleta dominante lejos de la marca (<2 colores cercanos).")

    # Contraste título vs fondo (WCAG AA)
    if expected_title_bbox and expected_title_color:
        fg = _hex_to_rgb(expected_title_color)
        bg = _sample_region_mean(img, expected_title_bbox)
        ratio = wcag_contrast(fg, bg)
        if ratio < 3.0:
            issues.append(
                f"Contraste del título {ratio:.2f}:1 muy bajo (mínimo WCAG AA grande = 3.0)."
            )
        elif ratio < 4.5:
            warnings.append(
                f"Contraste del título {ratio:.2f}:1 bajo para texto pequeño (AA pide 4.5)."
            )

    # Legibilidad mínima: bbox del título debe tener al menos 4% de altura de imagen
    if expected_title_bbox:
        h_frac = (expected_title_bbox[3] - expected_title_bbox[1]) / img.height
        if h_frac < 0.04:
            warnings.append(
                f"Altura del bloque de título {h_frac*100:.1f}% baja (recomendado ≥4%)."
            )

    # Logo visible
    if logo_bbox:
        issues.extend(_check_logo_area(img, logo_bbox))

    score = max(0.0, 1.0 - 0.25 * len(issues) - 0.05 * len(warnings))
    return BrandCheckResult(passed=not issues, issues=issues, warnings=warnings, score=score)


def validate_rendered_template(
    png_bytes: bytes,
    template_name: str,
    fmt_key: str | None = None,
) -> BrandCheckResult:
    """Conveniencia: valida una imagen sabiendo que se renderizó con una plantilla
    conocida. Usa los slots del spec para chequear contraste y logo."""
    from ..tools.template_renderer import load_template

    spec = load_template(template_name)
    title_slot = spec.slots.get("title")
    logo_slot = spec.slots.get("logo")

    # escalar bboxes si el png no está en tamaño del spec
    from PIL import Image as _PIL
    img = _PIL.open(io.BytesIO(png_bytes))
    W, H = img.size
    sw, sh = spec.size
    fx, fy = W / sw, H / sh

    def _scale(b):
        return (
            int(b[0] * fx), int(b[1] * fy),
            int(b[2] * fx), int(b[3] * fy),
        )

    return validate_image(
        png_bytes,
        fmt_key=fmt_key,
        expected_title_bbox=_scale(title_slot.bbox) if title_slot else None,
        expected_title_color=title_slot.color if title_slot else None,
        logo_bbox=_scale(logo_slot.bbox) if logo_slot else None,
    )
