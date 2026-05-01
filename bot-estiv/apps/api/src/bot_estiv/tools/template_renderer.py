"""Renderer de plantillas de overlay — motor de diseño profesional.

Una plantilla es un TemplateSpec (JSON) con:
- size: dimensiones finales del canvas
- slots: zonas para image / title / subtitle / pillar_tag / logo
- decorations: rects, hairlines, gradientes verticales, corner brackets

El renderer lee la spec + valores y produce PNG con Pillow.

En runtime hay dos fuentes de specs:
1. BUILTIN: plantillas hardcodeadas en este módulo (fallback siempre disponible).
2. packages/brand/templates/*.json: exportadas desde Figma via `figma_sync`.

Si el archivo JSON existe lo usa; si no, usa BUILTIN. Esto permite iterar en
Figma y que el código siga andando mientras tanto.
"""
from __future__ import annotations

import io
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw

from ..brand import PALETTE
from .canvas_design import _cover_resize, _load_font, _load_logo

logger = logging.getLogger(__name__)


def _templates_dir() -> Path:
    env_path = os.getenv("BRAND_TEMPLATES_DIR")
    candidates = [Path(env_path)] if env_path else []
    here = Path(__file__).resolve()
    candidates.append(Path("/app/packages/brand/templates"))
    candidates.extend(parent / "packages" / "brand" / "templates" for parent in here.parents)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else Path("packages/brand/templates")


_TEMPLATES_DIR = _templates_dir()


# ==========  Tipado de plantillas ==========

Bbox = tuple[int, int, int, int]  # (x1, y1, x2, y2)


@dataclass
class Slot:
    bbox: Bbox
    # image-only
    fit: Literal["cover", "contain"] = "cover"
    # text-only
    font_kind: str = "body"
    font_size_px: int | None = None
    font_ratio: float = 0.04  # si no hay font_size_px: size = ratio * canvas_h
    color: str = "#F5F1EA"
    align: Literal["left", "center", "right"] = "left"
    uppercase: bool = False
    tracking_em: float = 0.0  # espacio entre letras como fracción del ems
    line_spacing: float = 1.15
    max_lines: int = 3


@dataclass
class Decoration:
    type: Literal["rect", "hairline", "gradient_v", "corner_brackets"]
    bbox: Bbox
    fill: str = "#000000"
    opacity: float = 1.0
    weight: int = 2
    corner_len: int = 60  # para corner_brackets
    direction: Literal["top-down", "bottom-up"] = "bottom-up"


@dataclass
class TemplateSpec:
    name: str
    size: tuple[int, int]
    slots: dict[str, Slot]
    decorations: list[Decoration] = field(default_factory=list)


# ==========  Plantillas BUILTIN (fallback) ==========
#
# Referencia de slots: image, title, subtitle, pillar_tag, logo
# Las dims están pensadas para 1080×1350 (carousel_portrait / ig_feed_portrait).
# Se escalan proporcionalmente cuando el caller pide otro tamaño.


def _builtin_editorial_hero() -> TemplateSpec:
    W, H = 1080, 1350
    # Bloque inferior del 34% con gradient suave
    band_top = int(H * 0.66)
    return TemplateSpec(
        name="editorial_hero",
        size=(W, H),
        slots={
            "image": Slot(bbox=(0, 0, W, H), fit="cover"),
            "pillar_tag": Slot(
                bbox=(60, band_top + 45, 700, band_top + 80),
                font_kind="body_semibold",
                font_size_px=22,
                color=PALETTE.naranja_fuego,
                uppercase=True,
                tracking_em=0.28,
                max_lines=1,
            ),
            "title": Slot(
                bbox=(60, band_top + 100, W - 60, band_top + 280),
                font_kind="heading_bold",
                font_size_px=68,
                color=PALETTE.blanco_hueso,
                align="left",
                max_lines=2,
                line_spacing=1.08,
            ),
            "subtitle": Slot(
                bbox=(60, band_top + 300, W - 60, H - 80),
                font_kind="body_medium",
                font_size_px=26,
                color="#D9D3C7",
                align="left",
                max_lines=3,
                line_spacing=1.35,
            ),
            "logo": Slot(bbox=(W - 180, H - 110, W - 60, H - 60)),
        },
        decorations=[
            # gradient oscuro de bottom hacia arriba (empieza 150 px antes del band_top)
            Decoration(
                type="gradient_v",
                bbox=(0, band_top - 150, W, H),
                fill=PALETTE.gris_carbon,
                opacity=0.94,
                direction="bottom-up",
            ),
            # línea hairline naranja corta como acento sobre el pillar tag
            Decoration(
                type="hairline",
                bbox=(60, band_top + 28, 120, band_top + 30),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=2,
            ),
        ],
    )


def _builtin_minimal_stamp() -> TemplateSpec:
    W, H = 1080, 1350
    return TemplateSpec(
        name="minimal_stamp",
        size=(W, H),
        slots={
            "image": Slot(bbox=(0, 0, W, H), fit="cover"),
            "pillar_tag": Slot(
                bbox=(60, H - 130, 500, H - 100),
                font_kind="body_semibold",
                font_size_px=18,
                color=PALETTE.blanco_hueso,
                uppercase=True,
                tracking_em=0.3,
                max_lines=1,
            ),
            "logo": Slot(bbox=(W - 180, H - 130, W - 60, H - 80)),
        },
        decorations=[
            # sutil vignette inferior para que el logo y tag se lean
            Decoration(
                type="gradient_v",
                bbox=(0, int(H * 0.78), W, H),
                fill="#000000",
                opacity=0.55,
                direction="bottom-up",
            ),
        ],
    )


def _builtin_cover_hero() -> TemplateSpec:
    W, H = 1080, 1350
    return TemplateSpec(
        name="cover_hero",
        size=(W, H),
        slots={
            "image": Slot(bbox=(0, 0, W, H), fit="cover"),
            "title": Slot(
                bbox=(60, int(H * 0.58), W - 60, int(H * 0.86)),
                font_kind="heading_bold",
                font_size_px=92,
                color=PALETTE.blanco_hueso,
                align="left",
                max_lines=3,
                line_spacing=1.02,
            ),
            "subtitle": Slot(
                bbox=(60, int(H * 0.88), W - 60, H - 60),
                font_kind="body_medium",
                font_size_px=22,
                color="#E4DFD5",
                align="left",
                uppercase=True,
                tracking_em=0.18,
                max_lines=1,
            ),
            "logo": Slot(bbox=(W - 170, 60, W - 60, 110)),
        },
        decorations=[
            Decoration(
                type="gradient_v",
                bbox=(0, int(H * 0.35), W, H),
                fill="#14161A",
                opacity=0.85,
                direction="bottom-up",
            ),
            Decoration(
                type="hairline",
                bbox=(60, int(H * 0.56), 160, int(H * 0.56) + 2),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=3,
            ),
        ],
    )


def _builtin_split_60_40() -> TemplateSpec:
    W, H = 1080, 1350
    split_x = int(W * 0.60)
    return TemplateSpec(
        name="split_60_40",
        size=(W, H),
        slots={
            "image": Slot(bbox=(0, 0, split_x, H), fit="cover"),
            "pillar_tag": Slot(
                bbox=(split_x + 50, 140, W - 50, 180),
                font_kind="body_semibold",
                font_size_px=20,
                color=PALETTE.naranja_fuego,
                uppercase=True,
                tracking_em=0.28,
                max_lines=1,
            ),
            "title": Slot(
                bbox=(split_x + 50, 200, W - 50, 540),
                font_kind="heading_bold",
                font_size_px=52,
                color=PALETTE.blanco_hueso,
                align="left",
                max_lines=4,
                line_spacing=1.1,
            ),
            "subtitle": Slot(
                bbox=(split_x + 50, 560, W - 50, H - 200),
                font_kind="body_medium",
                font_size_px=22,
                color="#D9D3C7",
                align="left",
                max_lines=8,
                line_spacing=1.45,
            ),
            "logo": Slot(bbox=(split_x + 50, H - 140, split_x + 200, H - 80)),
        },
        decorations=[
            Decoration(
                type="rect",
                bbox=(split_x, 0, W, H),
                fill=PALETTE.gris_carbon,
                opacity=1.0,
            ),
            Decoration(
                type="hairline",
                bbox=(split_x + 50, 118, split_x + 130, 120),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=2,
            ),
        ],
    )


def _builtin_spec_card() -> TemplateSpec:
    W, H = 1080, 1350
    img_h = int(H * 0.60)
    return TemplateSpec(
        name="spec_card",
        size=(W, H),
        slots={
            "image": Slot(bbox=(0, 0, W, img_h), fit="cover"),
            "pillar_tag": Slot(
                bbox=(60, img_h + 50, W - 60, img_h + 85),
                font_kind="body_semibold",
                font_size_px=20,
                color=PALETTE.naranja_fuego,
                uppercase=True,
                tracking_em=0.28,
                max_lines=1,
            ),
            "title": Slot(
                bbox=(60, img_h + 110, W - 60, img_h + 270),
                font_kind="heading_bold",
                font_size_px=56,
                color=PALETTE.gris_carbon,
                align="left",
                max_lines=2,
                line_spacing=1.08,
            ),
            "subtitle": Slot(
                bbox=(60, img_h + 285, W - 60, H - 120),
                font_kind="body_medium",
                font_size_px=22,
                color=PALETTE.gris_suave,
                align="left",
                max_lines=5,
                line_spacing=1.45,
            ),
            "logo": Slot(bbox=(W - 180, H - 110, W - 60, H - 60)),
        },
        decorations=[
            Decoration(
                type="rect",
                bbox=(0, img_h, W, H),
                fill=PALETTE.blanco_hueso,
                opacity=1.0,
            ),
            Decoration(
                type="hairline",
                bbox=(60, img_h + 28, 140, img_h + 30),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=2,
            ),
            Decoration(
                type="corner_brackets",
                bbox=(30, img_h + 20, W - 30, H - 30),
                fill=PALETTE.gris_carbon,
                opacity=0.4,
                weight=2,
                corner_len=28,
            ),
        ],
    )


def _builtin_quote_card() -> TemplateSpec:
    """Tarjeta tipográfica para testimonios y frases de impacto (sin foto)."""
    W, H = 1080, 1350
    return TemplateSpec(
        name="quote_card",
        size=(W, H),
        slots={
            # no hay slot:image — fondo es el rect carbon
            "title": Slot(
                bbox=(90, int(H * 0.26), W - 90, int(H * 0.66)),
                font_kind="heading_bold",
                font_size_px=76,
                color=PALETTE.blanco_hueso,
                align="center",
                max_lines=4,
                line_spacing=1.18,
            ),
            "subtitle": Slot(
                bbox=(90, int(H * 0.68), W - 90, int(H * 0.80)),
                font_kind="body_medium",
                font_size_px=48,
                color=PALETTE.naranja_fuego,
                align="center",
                max_lines=2,
                line_spacing=1.25,
            ),
            "pillar_tag": Slot(
                bbox=(90, int(H * 0.82), W - 90, int(H * 0.87)),
                font_kind="body_semibold",
                font_size_px=22,
                color=PALETTE.naranja_fuego,
                align="center",
                uppercase=True,
                tracking_em=0.30,
                max_lines=1,
            ),
            # logo centrado en la parte inferior
            "logo": Slot(bbox=(W // 2 - 110, H - 120, W // 2 + 110, H - 60)),
        },
        decorations=[
            # fondo carbon completo
            Decoration(
                type="rect",
                bbox=(0, 0, W, H),
                fill=PALETTE.gris_carbon,
                opacity=1.0,
            ),
            # hairline superior
            Decoration(
                type="hairline",
                bbox=(90, int(H * 0.18), W - 90, int(H * 0.18) + 2),
                fill=PALETTE.naranja_fuego,
                opacity=0.7,
                weight=2,
            ),
            # hairline inferior
            Decoration(
                type="hairline",
                bbox=(90, int(H * 0.89), W - 90, int(H * 0.89) + 2),
                fill=PALETTE.naranja_fuego,
                opacity=0.7,
                weight=2,
            ),
        ],
    )


def _builtin_before_after() -> TemplateSpec:
    """Dos fotos lado a lado (antes/después) con leyenda inferior."""
    W, H = 1080, 1350
    split_x = W // 2
    img_h = int(H * 0.68)
    gap = 8  # px de separación entre las dos fotos
    return TemplateSpec(
        name="before_after",
        size=(W, H),
        slots={
            "image": Slot(bbox=(0, 0, split_x - gap // 2, img_h), fit="cover"),
            "image_b": Slot(bbox=(split_x + gap // 2, 0, W, img_h), fit="cover"),
            "pillar_tag": Slot(
                bbox=(60, img_h + 40, W - 60, img_h + 75),
                font_kind="body_semibold",
                font_size_px=20,
                color=PALETTE.naranja_fuego,
                uppercase=True,
                tracking_em=0.28,
                max_lines=1,
            ),
            "title": Slot(
                bbox=(60, img_h + 100, W - 60, img_h + 260),
                font_kind="heading_bold",
                font_size_px=56,
                color=PALETTE.gris_carbon,
                align="left",
                max_lines=2,
                line_spacing=1.08,
            ),
            "subtitle": Slot(
                bbox=(60, img_h + 278, W - 60, H - 120),
                font_kind="body_medium",
                font_size_px=22,
                color=PALETTE.gris_suave,
                align="left",
                max_lines=4,
                line_spacing=1.45,
            ),
            "logo": Slot(bbox=(W - 180, H - 110, W - 60, H - 60)),
        },
        decorations=[
            # panel inferior blanco hueso
            Decoration(
                type="rect",
                bbox=(0, img_h, W, H),
                fill=PALETTE.blanco_hueso,
                opacity=1.0,
            ),
            # franja blanca de separación entre fotos
            Decoration(
                type="rect",
                bbox=(split_x - gap // 2, 0, split_x + gap // 2, img_h),
                fill=PALETTE.blanco_hueso,
                opacity=1.0,
            ),
            # hairline naranja sobre el pillar tag
            Decoration(
                type="hairline",
                bbox=(60, img_h + 18, 140, img_h + 20),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=2,
            ),
        ],
    )


_BUILTIN: dict[str, TemplateSpec] = {
    "editorial_hero": _builtin_editorial_hero(),
    "minimal_stamp": _builtin_minimal_stamp(),
    "cover_hero": _builtin_cover_hero(),
    "split_60_40": _builtin_split_60_40(),
    "spec_card": _builtin_spec_card(),
    "quote_card": _builtin_quote_card(),
    "before_after": _builtin_before_after(),
}


# ==========  Helpers de serialización Figma → Spec ==========

def _spec_from_dict(data: dict) -> TemplateSpec:
    slots = {
        name: Slot(**s) for name, s in (data.get("slots") or {}).items()
    }
    decos = [Decoration(**d) for d in (data.get("decorations") or [])]
    return TemplateSpec(
        name=data["name"],
        size=tuple(data.get("size", (1080, 1350))),  # type: ignore[arg-type]
        slots=slots,
        decorations=decos,
    )


def load_template(name: str) -> TemplateSpec:
    """Busca primero en packages/brand/templates/{name}.json; si no hay, builtin."""
    path = _TEMPLATES_DIR / f"{name}.json"
    if path.exists():
        try:
            return _spec_from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            logger.warning(
                "template.load_failed",
                extra={"name": name, "path": str(path), "err": str(exc)},
            )
    if name not in _BUILTIN:
        logger.warning("template.unknown", extra={"name": name})
        return _BUILTIN["editorial_hero"]
    return _BUILTIN[name]


def list_templates() -> list[str]:
    names = set(_BUILTIN.keys())
    if _TEMPLATES_DIR.exists():
        for p in _TEMPLATES_DIR.glob("*.json"):
            names.add(p.stem)
    return sorted(names)


# ==========  Rendering ==========


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, int(alpha * 255))


def _scale_spec(spec: TemplateSpec, target_w: int, target_h: int) -> TemplateSpec:
    """Escala los bboxes/tamaños de la spec al canvas destino."""
    sw, sh = spec.size
    if (sw, sh) == (target_w, target_h):
        return spec
    fx, fy = target_w / sw, target_h / sh

    def scale_bbox(b: Bbox) -> Bbox:
        return (int(b[0] * fx), int(b[1] * fy), int(b[2] * fx), int(b[3] * fy))

    new_slots = {}
    for name, s in spec.slots.items():
        size_px = int(s.font_size_px * fy) if s.font_size_px else None
        new_slots[name] = Slot(
            bbox=scale_bbox(s.bbox),
            fit=s.fit,
            font_kind=s.font_kind,
            font_size_px=size_px,
            font_ratio=s.font_ratio,
            color=s.color,
            align=s.align,
            uppercase=s.uppercase,
            tracking_em=s.tracking_em,
            line_spacing=s.line_spacing,
            max_lines=s.max_lines,
        )

    new_decs = [
        Decoration(
            type=d.type,
            bbox=scale_bbox(d.bbox),
            fill=d.fill,
            opacity=d.opacity,
            weight=max(1, int(d.weight * fy)),
            corner_len=int(d.corner_len * fy),
            direction=d.direction,
        )
        for d in spec.decorations
    ]
    return TemplateSpec(
        name=spec.name, size=(target_w, target_h), slots=new_slots, decorations=new_decs
    )


def _draw_text_with_tracking(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    fill,
    tracking_em: float,
) -> int:
    """Dibuja texto con letter-spacing (tracking). Devuelve el ancho total."""
    x, y = xy
    if not tracking_em:
        draw.text((x, y), text, fill=fill, font=font)
        bbox = draw.textbbox((x, y), text, font=font)
        return bbox[2] - bbox[0]
    # aprox 1em ≈ font.size
    spacing_px = int(getattr(font, "size", 20) * tracking_em)
    cursor = x
    for ch in text:
        draw.text((cursor, y), ch, fill=fill, font=font)
        w = draw.textbbox((0, 0), ch, font=font)[2]
        cursor += w + spacing_px
    return cursor - x


def _wrap(
    text: str,
    font,
    max_w: int,
    draw: ImageDraw.ImageDraw,
    tracking_em: float = 0.0,
    max_lines: int | None = None,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    spacing_px = int(getattr(font, "size", 20) * tracking_em) if tracking_em else 0

    def measured_width(s: str) -> int:
        if not s:
            return 0
        if not tracking_em:
            bb = draw.textbbox((0, 0), s, font=font)
            return bb[2] - bb[0]
        # con tracking, sumo ancho de cada char + spacing
        total = 0
        for ch in s:
            cb = draw.textbbox((0, 0), ch, font=font)
            total += (cb[2] - cb[0]) + spacing_px
        return max(0, total - spacing_px)

    for w in words:
        trial = f"{cur} {w}".strip()
        if measured_width(trial) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
        if max_lines and len(lines) >= max_lines:
            break
    if cur and (not max_lines or len(lines) < max_lines):
        lines.append(cur)
    # truncar con elipsis si pasamos max_lines
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return lines


def _draw_decoration(base: Image.Image, deco: Decoration) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x1, y1, x2, y2 = deco.bbox

    if deco.type == "rect":
        draw.rectangle([(x1, y1), (x2, y2)], fill=_hex_to_rgba(deco.fill, deco.opacity))

    elif deco.type == "hairline":
        draw.rectangle([(x1, y1), (x2, y2)], fill=_hex_to_rgba(deco.fill, deco.opacity))

    elif deco.type == "gradient_v":
        w, h = max(1, x2 - x1), max(1, y2 - y1)
        for i in range(h):
            t = i / max(1, h - 1)
            if deco.direction == "bottom-up":
                a = deco.opacity * t
            else:
                a = deco.opacity * (1 - t)
            overlay.paste(
                Image.new("RGBA", (w, 1), _hex_to_rgba(deco.fill, a)),
                (x1, y1 + i),
            )

    elif deco.type == "corner_brackets":
        clr = _hex_to_rgba(deco.fill, deco.opacity)
        cl = deco.corner_len
        w = deco.weight
        # top-left
        draw.rectangle([(x1, y1), (x1 + cl, y1 + w)], fill=clr)
        draw.rectangle([(x1, y1), (x1 + w, y1 + cl)], fill=clr)
        # top-right
        draw.rectangle([(x2 - cl, y1), (x2, y1 + w)], fill=clr)
        draw.rectangle([(x2 - w, y1), (x2, y1 + cl)], fill=clr)
        # bottom-left
        draw.rectangle([(x1, y2 - w), (x1 + cl, y2)], fill=clr)
        draw.rectangle([(x1, y2 - cl), (x1 + w, y2)], fill=clr)
        # bottom-right
        draw.rectangle([(x2 - cl, y2 - w), (x2, y2)], fill=clr)
        draw.rectangle([(x2 - w, y2 - cl), (x2, y2)], fill=clr)

    base.alpha_composite(overlay)


def _draw_image_slot(base: Image.Image, slot: Slot, src: Image.Image) -> None:
    x1, y1, x2, y2 = slot.bbox
    w, h = x2 - x1, y2 - y1
    if slot.fit == "cover":
        fitted = _cover_resize(src.convert("RGB"), w, h)
    else:  # contain
        sw, sh = src.size
        ratio = min(w / sw, h / sh)
        nw, nh = int(sw * ratio), int(sh * ratio)
        fitted = src.resize((nw, nh), Image.LANCZOS)
        container = Image.new("RGB", (w, h), "#000000")
        container.paste(fitted, ((w - nw) // 2, (h - nh) // 2))
        fitted = container
    base.paste(fitted.convert("RGBA"), (x1, y1))


def _draw_text_slot(base: Image.Image, slot: Slot, text: str) -> None:
    x1, y1, x2, y2 = slot.bbox
    max_w = x2 - x1

    if slot.uppercase:
        text = text.upper()

    font_size = slot.font_size_px or max(12, int(base.size[1] * slot.font_ratio))
    font = _load_font(slot.font_kind, font_size)
    draw = ImageDraw.Draw(base)

    lines = _wrap(text, font, max_w, draw, slot.tracking_em, slot.max_lines)
    line_h = int(font_size * slot.line_spacing)

    for i, line in enumerate(lines):
        y = y1 + i * line_h
        if y + line_h > y2:
            break
        # alineación
        if slot.align == "left":
            x = x1
        else:
            line_w = (
                _measure_line_width(line, font, draw, slot.tracking_em)
                if slot.tracking_em
                else draw.textbbox((0, 0), line, font=font)[2]
                - draw.textbbox((0, 0), line, font=font)[0]
            )
            x = x1 + (max_w - line_w) if slot.align == "right" else x1 + (max_w - line_w) // 2

        _draw_text_with_tracking(
            draw, (x, y), line, font, _hex_to_rgba(slot.color, 1.0), slot.tracking_em
        )


def _measure_line_width(line: str, font, draw, tracking_em: float) -> int:
    if not tracking_em:
        bb = draw.textbbox((0, 0), line, font=font)
        return bb[2] - bb[0]
    spacing_px = int(getattr(font, "size", 20) * tracking_em)
    total = 0
    for ch in line:
        cb = draw.textbbox((0, 0), ch, font=font)
        total += (cb[2] - cb[0]) + spacing_px
    return max(0, total - spacing_px)


def _draw_logo_slot(base: Image.Image, slot: Slot) -> None:
    logo = _load_logo()
    if logo is None:
        return
    x1, y1, x2, y2 = slot.bbox
    w, h = x2 - x1, y2 - y1
    # contain, centrado
    sw, sh = logo.size
    ratio = min(w / sw, h / sh)
    nw, nh = int(sw * ratio), int(sh * ratio)
    resized = logo.resize((nw, nh), Image.LANCZOS)
    cx = x1 + (w - nw) // 2
    cy = y1 + (h - nh) // 2
    base.alpha_composite(resized, (cx, cy))


# ==========  API pública ==========


def render(
    spec: TemplateSpec | str,
    values: dict[str, str | bytes | Image.Image | None],
    target_size: tuple[int, int] | None = None,
) -> bytes:
    """Renderiza una pieza usando la spec y valores provistos.

    `values` admite:
      - image: bytes (PNG/JPG) | PIL.Image | None
      - title, subtitle, pillar_tag: str | None
      - (logo lo carga automáticamente desde settings.brand_logo_abs)

    Devuelve PNG en bytes.
    """
    if isinstance(spec, str):
        spec = load_template(spec)

    W, H = target_size or spec.size
    spec = _scale_spec(spec, W, H)

    base = Image.new("RGBA", (W, H), "#000000FF")

    # 1) imagen(es) de fondo
    for slot_key in ("image", "image_b"):
        img_val = values.get(slot_key)
        if img_val is not None and slot_key in spec.slots:
            if isinstance(img_val, bytes):
                with Image.open(io.BytesIO(img_val)) as img:
                    _draw_image_slot(base, spec.slots[slot_key], img)
            elif isinstance(img_val, Image.Image):
                _draw_image_slot(base, spec.slots[slot_key], img_val)

    # 2) decoraciones
    for deco in spec.decorations:
        _draw_decoration(base, deco)

    # 3) textos
    for slot_name in ("pillar_tag", "title", "subtitle"):
        txt = values.get(slot_name)
        if txt and slot_name in spec.slots:
            _draw_text_slot(base, spec.slots[slot_name], str(txt))

    # 4) logo
    if "logo" in spec.slots and values.get("logo") is not False:
        _draw_logo_slot(base, spec.slots["logo"])

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
