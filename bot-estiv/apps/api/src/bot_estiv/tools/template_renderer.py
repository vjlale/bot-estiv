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
    type: Literal[
        "rect",
        "hairline",
        "gradient_v",
        "corner_brackets",
        "dimension_line",
        "numbered_badge",
        "callout_panel",
    ]
    bbox: Bbox
    fill: str = "#000000"
    opacity: float = 1.0
    weight: int = 2
    corner_len: int = 60  # para corner_brackets
    direction: Literal["top-down", "bottom-up"] = "bottom-up"
    # ---- dimension_line ----
    orientation: Literal["h", "v"] = "h"
    tick_len: int = 12
    label: str | None = None
    label_font_kind: str = "body_medium"
    label_font_size_px: int = 22
    label_color: str = "#36454F"
    label_bg: str | None = None  # fondo del label (ej: "#F5F1EA") para legibilidad
    # ---- numbered_badge ----
    number: int = 1
    radius: int = 26
    text_color: str = "#F5F1EA"
    line_to: tuple[int, int] | None = None  # punto final de la lead line
    # ---- callout_panel ----
    panel_title: str | None = None
    panel_body: str | None = None
    panel_title_font_kind: str = "body_semibold"
    panel_body_font_kind: str = "body_medium"
    panel_title_color: str = "#36454F"
    panel_body_color: str = "#4E5A66"
    panel_radius: int = 8
    panel_padding: int = 24


@dataclass
class TemplateSpec:
    name: str
    size: tuple[int, int]
    slots: dict[str, Slot]
    decorations: list[Decoration] = field(default_factory=list)
    background_color: str = "#000000"  # color de canvas antes de dibujar image/decos


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
def _builtin_infographic_dimensions() -> TemplateSpec:
    """Replicando la ref de la mesa 2.20 m — canvas landscape 1920x1080.

    Slots asignados por el caller:
      - image: producto aislado (NB2 clean)
      - title: titular principal
      - dim_top_label: texto de la dimensión superior (ej "2,20 metros de largo")
      - dim_right_label: texto de la dimensión lateral
      - description_title, description_body: panel descriptivo abajo derecha
      - logo: el logo Gardens Wood
    """
    W, H = 1920, 1080
    IMG_X1, IMG_Y1, IMG_X2, IMG_Y2 = 260, 200, 1400, 820

    return TemplateSpec(
        name="infographic_dimensions",
        size=(W, H),
        background_color="#F5F1EA",
        slots={
            "image": Slot(bbox=(IMG_X1, IMG_Y1, IMG_X2, IMG_Y2), fit="contain"),
            "title": Slot(
                bbox=(80, 40, W - 120, 140),
                font_kind="heading_bold",
                font_size_px=60,
                color="#36454F",
                align="left",
                max_lines=1,
                line_spacing=1.05,
            ),
            "dim_top_label": Slot(
                bbox=(IMG_X1, IMG_Y1 - 90, IMG_X2, IMG_Y1 - 50),
                font_kind="body_medium",
                font_size_px=26,
                color="#36454F",
                align="center",
                max_lines=1,
            ),
            "dim_right_label": Slot(
                bbox=(
                    IMG_X2 + 80,
                    (IMG_Y1 + IMG_Y2) // 2 - 70,
                    W - 40,
                    (IMG_Y1 + IMG_Y2) // 2 + 70,
                ),
                font_kind="body_medium",
                font_size_px=22,
                color="#36454F",
                align="left",
                max_lines=3,
                line_spacing=1.3,
            ),
            "description_title": Slot(
                bbox=(1020, 860, W - 60, 900),
                font_kind="body_semibold",
                font_size_px=18,
                color=PALETTE.naranja_fuego,
                align="left",
                uppercase=True,
                tracking_em=0.24,
                max_lines=1,
            ),
            "description_body": Slot(
                bbox=(1020, 910, W - 60, 1020),
                font_kind="body_medium",
                font_size_px=22,
                color="#4E5A66",
                align="left",
                max_lines=4,
                line_spacing=1.35,
            ),
            "logo": Slot(bbox=(80, H - 90, 220, H - 40)),
        },
        decorations=[
            # dimension line horizontal arriba de la imagen
            Decoration(
                type="dimension_line",
                bbox=(IMG_X1, IMG_Y1 - 35, IMG_X2, IMG_Y1 - 25),
                orientation="h",
                fill="#36454F",
                weight=2,
                tick_len=16,
            ),
            # dimension line vertical a la derecha de la imagen
            Decoration(
                type="dimension_line",
                bbox=(IMG_X2 + 30, IMG_Y1, IMG_X2 + 40, IMG_Y2),
                orientation="v",
                fill="#36454F",
                weight=2,
                tick_len=16,
            ),
            # panel de fondo para description (opacity alta → blanco hueso limpio)
            Decoration(
                type="callout_panel",
                bbox=(1000, 840, W - 40, 1040),
                fill="#F5F1EA",
                opacity=0.96,
                panel_radius=6,
                panel_padding=0,  # texto manejado por slots description_*
            ),
            # hairline de acento arriba izq (debajo del título)
            Decoration(
                type="hairline",
                bbox=(80, 160, 180, 162),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=2,
            ),
            # hairline del panel (entre title y body)
            Decoration(
                type="hairline",
                bbox=(1020, 902, 1100, 903),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=1,
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
def _builtin_numbered_steps() -> TemplateSpec:
    """Replicando la ref del cerco 'Ingeniería Oculta' — canvas 1920x1080.

    Slots asignados por el caller:
      - image: producto/escena (NB2 clean)
      - title: titular
      - step_1_title, step_1_body, step_2_*, step_3_* (texto de cada callout)
      - logo
    """
    W, H = 1920, 1080
    IMG_X1, IMG_Y1, IMG_X2, IMG_Y2 = 700, 280, 1220, 820

    # posiciones de los 3 badges (centros)
    B1_CX, B1_CY = 120, 360
    B2_CX, B2_CY = W - 120, 360
    B3_CX, B3_CY = W - 120, 760

    # panels (cajas detras del texto de cada step)
    P1 = (60, 410, 640, 620)
    P2 = (W - 640, 410, W - 60, 620)
    P3 = (W - 640, 810, W - 60, 1020)

    return TemplateSpec(
        name="numbered_steps",
        size=(W, H),
        background_color="#EEEBE3",
        slots={
            "image": Slot(bbox=(IMG_X1, IMG_Y1, IMG_X2, IMG_Y2), fit="contain"),
            "title": Slot(
                bbox=(80, 40, W - 80, 160),
                font_kind="heading",
                font_size_px=56,
                color="#36454F",
                align="center",
                max_lines=1,
            ),
            # STEP 1
            "step_1_title": Slot(
                bbox=(P1[0] + 24, P1[1] + 22, P1[2] - 24, P1[1] + 62),
                font_kind="body_semibold",
                font_size_px=22,
                color="#36454F",
                align="left",
                max_lines=1,
            ),
            "step_1_body": Slot(
                bbox=(P1[0] + 24, P1[1] + 72, P1[2] - 24, P1[3] - 20),
                font_kind="body_medium",
                font_size_px=20,
                color="#4E5A66",
                align="left",
                max_lines=6,
                line_spacing=1.35,
            ),
            # STEP 2
            "step_2_title": Slot(
                bbox=(P2[0] + 24, P2[1] + 22, P2[2] - 24, P2[1] + 62),
                font_kind="body_semibold",
                font_size_px=22,
                color="#36454F",
                align="left",
                max_lines=1,
            ),
            "step_2_body": Slot(
                bbox=(P2[0] + 24, P2[1] + 72, P2[2] - 24, P2[3] - 20),
                font_kind="body_medium",
                font_size_px=20,
                color="#4E5A66",
                align="left",
                max_lines=6,
                line_spacing=1.35,
            ),
            # STEP 3
            "step_3_title": Slot(
                bbox=(P3[0] + 24, P3[1] + 22, P3[2] - 24, P3[1] + 62),
                font_kind="body_semibold",
                font_size_px=22,
                color="#36454F",
                align="left",
                max_lines=1,
            ),
            "step_3_body": Slot(
                bbox=(P3[0] + 24, P3[1] + 72, P3[2] - 24, P3[3] - 20),
                font_kind="body_medium",
                font_size_px=20,
                color="#4E5A66",
                align="left",
                max_lines=6,
                line_spacing=1.35,
            ),
            "logo": Slot(bbox=(80, H - 80, 220, H - 40)),
        },
        decorations=[
            # hairline naranja debajo del título
            Decoration(
                type="hairline",
                bbox=(W // 2 - 60, 170, W // 2 + 60, 172),
                fill=PALETTE.naranja_fuego,
                opacity=1.0,
                weight=2,
            ),
            # panels detrás de cada step (quedan DEBAJO de los textos — se dibujan antes)
            Decoration(
                type="callout_panel",
                bbox=P1,
                fill="#F5F1EA",
                opacity=0.97,
                panel_radius=6,
                panel_padding=0,
            ),
            Decoration(
                type="callout_panel",
                bbox=P2,
                fill="#F5F1EA",
                opacity=0.97,
                panel_radius=6,
                panel_padding=0,
            ),
            Decoration(
                type="callout_panel",
                bbox=P3,
                fill="#F5F1EA",
                opacity=0.97,
                panel_radius=6,
                panel_padding=0,
            ),
            # badges (se dibujan DESPUÉS para quedar por encima de las leadlines sobre panels)
            Decoration(
                type="numbered_badge",
                bbox=(B1_CX - 30, B1_CY - 30, B1_CX + 30, B1_CY + 30),
                number=1,
                radius=30,
                fill=PALETTE.verde_eucalipto,
                text_color="#F5F1EA",
                weight=2,
                line_to=(IMG_X1 + 40, IMG_Y1 + 120),
            ),
            Decoration(
                type="numbered_badge",
                bbox=(B2_CX - 30, B2_CY - 30, B2_CX + 30, B2_CY + 30),
                number=2,
                radius=30,
                fill=PALETTE.verde_eucalipto,
                text_color="#F5F1EA",
                weight=2,
                line_to=(IMG_X2 - 60, IMG_Y1 + 180),
            ),
            Decoration(
                type="numbered_badge",
                bbox=(B3_CX - 30, B3_CY - 30, B3_CX + 30, B3_CY + 30),
                number=3,
                radius=30,
                fill=PALETTE.verde_eucalipto,
                text_color="#F5F1EA",
                weight=2,
                line_to=(IMG_X2 - 80, IMG_Y2 - 160),
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
    "infographic_dimensions": _builtin_infographic_dimensions(),
    "numbered_steps": _builtin_numbered_steps(),
}


# ==========  Helpers de serialización Figma → Spec ==========

def _spec_from_dict(data: dict) -> TemplateSpec:
    slots = {
        name: Slot(**s) for name, s in (data.get("slots") or {}).items()
    }
    decos: list[Decoration] = []
    for d in data.get("decorations") or []:
        raw = dict(d)
        # bbox y line_to vienen como list desde JSON → tuplear
        if "bbox" in raw and raw["bbox"] is not None:
            raw["bbox"] = tuple(raw["bbox"])
        if raw.get("line_to") is not None:
            raw["line_to"] = tuple(raw["line_to"])
        decos.append(Decoration(**raw))
    return TemplateSpec(
        name=data["name"],
        size=tuple(data.get("size", (1080, 1350))),  # type: ignore[arg-type]
        slots=slots,
        decorations=decos,
        background_color=data.get("background_color", "#000000"),
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
                extra={"template_name": name, "path": str(path), "err": str(exc)},
            )
    if name not in _BUILTIN:
        logger.warning("template.unknown", extra={"template_name": name})
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
    if len(h) == 3:
        # shortcut #RGB → #RRGGBB
        h = "".join(c * 2 for c in h)
    if len(h) < 6:
        raise ValueError(f"Invalid hex color: {hex_color!r}")
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

    new_decs = []
    for d in spec.decorations:
        line_to = None
        if d.line_to is not None:
            line_to = (int(d.line_to[0] * fx), int(d.line_to[1] * fy))
        new_decs.append(
            Decoration(
                type=d.type,
                bbox=scale_bbox(d.bbox),
                fill=d.fill,
                opacity=d.opacity,
                weight=max(1, int(d.weight * fy)),
                corner_len=int(d.corner_len * fy),
                direction=d.direction,
                orientation=d.orientation,
                tick_len=int(d.tick_len * fy),
                label=d.label,
                label_font_kind=d.label_font_kind,
                label_font_size_px=int(d.label_font_size_px * fy),
                label_color=d.label_color,
                label_bg=d.label_bg,
                number=d.number,
                radius=int(d.radius * fy),
                text_color=d.text_color,
                line_to=line_to,
                panel_title=d.panel_title,
                panel_body=d.panel_body,
                panel_title_font_kind=d.panel_title_font_kind,
                panel_body_font_kind=d.panel_body_font_kind,
                panel_title_color=d.panel_title_color,
                panel_body_color=d.panel_body_color,
                panel_radius=int(d.panel_radius * fy),
                panel_padding=int(d.panel_padding * fy),
            )
        )
    return TemplateSpec(
        name=spec.name,
        size=(target_w, target_h),
        slots=new_slots,
        decorations=new_decs,
        background_color=spec.background_color,
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

    elif deco.type == "dimension_line":
        _draw_dimension_line(base, overlay, draw, deco)

    elif deco.type == "numbered_badge":
        _draw_numbered_badge(base, overlay, draw, deco)

    elif deco.type == "callout_panel":
        _draw_callout_panel(base, overlay, draw, deco)

    base.alpha_composite(overlay)


def _draw_dimension_line(
    base: Image.Image,
    overlay: Image.Image,
    draw: ImageDraw.ImageDraw,
    deco: Decoration,
) -> None:
    """Línea de dimensión con tick marks perpendiculares en los extremos y
    un label centrado (con un rect blanco detrás si `label_bg` está seteado).
    """
    x1, y1, x2, y2 = deco.bbox
    clr = _hex_to_rgba(deco.fill, deco.opacity)
    w = max(1, deco.weight)
    tl = deco.tick_len

    if deco.orientation == "h":
        # línea horizontal centrada en (y1+y2)/2 entre x1..x2
        cy = (y1 + y2) // 2
        draw.rectangle([(x1, cy - w // 2), (x2, cy - w // 2 + w)], fill=clr)
        # ticks verticales en los extremos
        draw.rectangle(
            [(x1, cy - tl), (x1 + w, cy + tl)], fill=clr
        )
        draw.rectangle(
            [(x2 - w, cy - tl), (x2, cy + tl)], fill=clr
        )
    else:  # "v"
        cx = (x1 + x2) // 2
        draw.rectangle([(cx - w // 2, y1), (cx - w // 2 + w, y2)], fill=clr)
        draw.rectangle(
            [(cx - tl, y1), (cx + tl, y1 + w)], fill=clr
        )
        draw.rectangle(
            [(cx - tl, y2 - w), (cx + tl, y2)], fill=clr
        )

    if deco.label:
        font = _load_font(deco.label_font_kind, deco.label_font_size_px)
        bb = draw.textbbox((0, 0), deco.label, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if deco.orientation == "h":
            cx = (x1 + x2) // 2
            tx = cx - tw // 2
            ty = (y1 + y2) // 2 - th - 14  # arriba de la línea
        else:
            cy = (y1 + y2) // 2
            tx = (x1 + x2) // 2 + 18  # a la derecha del eje
            ty = cy - th // 2
        # fondo optional (círculo/rectángulo blanco para legibilidad)
        if deco.label_bg:
            pad = 8
            draw.rectangle(
                [(tx - pad, ty - pad), (tx + tw + pad, ty + th + pad)],
                fill=_hex_to_rgba(deco.label_bg, 0.92),
            )
        draw.text((tx, ty), deco.label, fill=_hex_to_rgba(deco.label_color, 1.0), font=font)


def _draw_numbered_badge(
    base: Image.Image,
    overlay: Image.Image,
    draw: ImageDraw.ImageDraw,
    deco: Decoration,
) -> None:
    """Círculo con número adentro; opcional lead-line a `line_to`."""
    x1, y1, x2, y2 = deco.bbox
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    r = deco.radius

    # lead-line al punto indicado (ANTES del círculo para que quede por debajo)
    if deco.line_to is not None:
        lx, ly = deco.line_to
        draw.line(
            [(cx, cy), (int(lx), int(ly))],
            fill=_hex_to_rgba(deco.fill, deco.opacity),
            width=max(1, deco.weight),
        )
        # pequeño punto en el destino
        dot_r = max(3, deco.weight + 2)
        draw.ellipse(
            [(int(lx) - dot_r, int(ly) - dot_r), (int(lx) + dot_r, int(ly) + dot_r)],
            fill=_hex_to_rgba(deco.fill, deco.opacity),
        )

    # círculo del badge
    draw.ellipse(
        [(cx - r, cy - r), (cx + r, cy + r)],
        fill=_hex_to_rgba(deco.fill, deco.opacity),
    )

    # número centrado
    font = _load_font("body_bold", int(r * 1.05))
    text = str(deco.number)
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    # correccion por baseline offset del font
    baseline_offset = bb[1]
    draw.text(
        (cx - tw // 2 - bb[0], cy - th // 2 - baseline_offset),
        text,
        fill=_hex_to_rgba(deco.text_color, 1.0),
        font=font,
    )


def _draw_callout_panel(
    base: Image.Image,
    overlay: Image.Image,
    draw: ImageDraw.ImageDraw,
    deco: Decoration,
) -> None:
    """Panel translúcido con título arriba y cuerpo abajo, esquinas redondeadas."""
    x1, y1, x2, y2 = deco.bbox
    # panel fill
    radius = deco.panel_radius
    fill_rgba = _hex_to_rgba(deco.fill, deco.opacity)
    try:
        draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=radius, fill=fill_rgba)
    except Exception:  # noqa: BLE001 - fallback a rect si no soporta rounded
        draw.rectangle([(x1, y1), (x2, y2)], fill=fill_rgba)

    pad = deco.panel_padding
    inner_w = (x2 - x1) - 2 * pad
    cursor_y = y1 + pad

    # título (semibold, 1 línea, sin wrap)
    if deco.panel_title:
        tf = _load_font(deco.panel_title_font_kind, deco.label_font_size_px)
        tl = _wrap(
            deco.panel_title, tf, inner_w, draw, tracking_em=0.0, max_lines=1
        )
        for line in tl:
            draw.text(
                (x1 + pad, cursor_y),
                line,
                fill=_hex_to_rgba(deco.panel_title_color, 1.0),
                font=tf,
            )
            line_h = draw.textbbox((0, 0), line, font=tf)[3] + 6
            cursor_y += line_h

    # body (medium, wrap con max_lines reasonable según altura disponible)
    if deco.panel_body:
        bf_size = max(14, int(deco.label_font_size_px * 0.85))
        bf = _load_font(deco.panel_body_font_kind, bf_size)
        line_h = int(bf_size * 1.35)
        remaining_h = (y2 - pad) - cursor_y
        max_lines = max(1, remaining_h // line_h)
        lines = _wrap(
            deco.panel_body,
            bf,
            inner_w,
            draw,
            tracking_em=0.0,
            max_lines=max_lines,
        )
        for line in lines:
            draw.text(
                (x1 + pad, cursor_y),
                line,
                fill=_hex_to_rgba(deco.panel_body_color, 1.0),
                font=bf,
            )
            cursor_y += line_h


def _draw_image_slot(base: Image.Image, slot: Slot, src: Image.Image) -> None:
    x1, y1, x2, y2 = slot.bbox
    w, h = x2 - x1, y2 - y1
    if slot.fit == "cover":
        fitted = _cover_resize(src.convert("RGB"), w, h).convert("RGBA")
        base.paste(fitted, (x1, y1))
    else:  # contain: preserva transparencia del src
        sw, sh = src.size
        ratio = min(w / sw, h / sh)
        nw, nh = max(1, int(sw * ratio)), max(1, int(sh * ratio))
        fitted = src.convert("RGBA").resize((nw, nh), Image.LANCZOS)
        cx = x1 + (w - nw) // 2
        cy = y1 + (h - nh) // 2
        base.alpha_composite(fitted, (cx, cy))


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

    # color de fondo del canvas (antes de imagen y decoraciones)
    bg_hex = spec.background_color or "#000000"
    r, g, b, _ = _hex_to_rgba(bg_hex, 1.0)
    base = Image.new("RGBA", (W, H), (r, g, b, 255))

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

    # 3) textos — renderiza cualquier slot de texto que tenga valor en `values`
    #    (excluye los slots "especiales": image, logo)
    for slot_name, slot in spec.slots.items():
        if slot_name in ("image", "logo"):
            continue
        txt = values.get(slot_name)
        if txt:
            _draw_text_slot(base, slot, str(txt))

    # 4) logo
    if "logo" in spec.slots and values.get("logo") is not False:
        _draw_logo_slot(base, spec.slots["logo"])

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
