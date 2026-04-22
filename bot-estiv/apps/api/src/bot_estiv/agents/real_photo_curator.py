"""RealPhotoCurator: cura un set de fotos REALES de una obra y arma el carrusel.

Responsabilidades:
1. Decidir la portada (foto más "editorial" para el formato destino).
2. Ordenar el resto en roles narrativos: apertura → detalle → lifestyle → cierre.
3. Devolver una lista de SlideBrief lista para que el ContentDesigner
   los procese por el pipeline de fotos reales (sin AI generativa).

Heurística pura (sin LLM). Para casos extremos se puede extender luego con
captions de Gemini multimodal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from ..schemas import SlideBrief
from ..tools import photo_editor

logger = logging.getLogger(__name__)


# Roles narrativos por posición del carrusel (1..5)
NARRATIVE_ROLES: dict[int, str] = {
    1: "apertura",   # la foto portada, plano amplio
    2: "detalle",    # close-up / textura / unión
    3: "lifestyle",  # espacio habitado / plano medio
    4: "cierre",     # plano final con aire para CTA
    5: "spec",       # ficha técnica con datos del proyecto
}

# Plantilla sugerida por rol (cae en default si no coincide)
TEMPLATE_BY_ROLE: dict[str, str] = {
    "apertura": "cover_hero",
    "detalle": "minimal_stamp",
    "lifestyle": "editorial_hero",
    "cierre": "split_60_40",
    "spec": "spec_card",
}


@dataclass
class CuratedPhoto:
    index: int        # posición en el set original
    role: str         # apertura | detalle | lifestyle | cierre | spec
    template: str
    slide_position: int  # 1..N en el carrusel final


@dataclass
class CuratedSet:
    topic: str
    cover_index: int
    order: list[CuratedPhoto]   # longitud = n_slides, cada uno apunta a un index del set original
    skipped_indices: list[int]  # fotos no usadas


def _load_as_pil(src: Path | bytes | Image.Image) -> Image.Image:
    if isinstance(src, (str, Path)):
        img = Image.open(Path(src))
    elif isinstance(src, bytes):
        import io
        img = Image.open(io.BytesIO(src))
    else:
        img = src
    return ImageOps.exif_transpose(img).convert("RGB")


def _detail_score(img: Image.Image) -> float:
    """Alta textura + bajo aspect_match ideal = foto de detalle/primer plano."""
    return photo_editor._sharpness(img)


def _openness_score(img: Image.Image) -> float:
    """Foto más 'abierta': más uniformidad en el canal L (menos varianza)."""
    gray = img.convert("L")
    small = gray.copy()
    small.thumbnail((320, 320))
    pixels = list(small.getdata())
    if not pixels:
        return 0.0
    mean = sum(pixels) / len(pixels)
    var = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    # invertir: menos varianza = más "abierto"
    return max(0.0, 1.0 - min(1.0, var / 4000.0))


def curate(
    photos: list[Path | bytes | Image.Image],
    topic: str,
    n_slides: int = 4,
    fmt_key: str = "ig_feed_portrait",
) -> CuratedSet:
    """Cura el set y devuelve órden narrativo + rol por foto.

    Usa heurística sin AI:
    - cover = pick_cover (sharpness + regla de tercios + aspect match)
    - detalle = mayor sharpness entre el resto
    - lifestyle = mejor rule_of_thirds entre el resto
    - cierre = mayor openness (planos amplios)
    """
    if not photos:
        raise ValueError("curate: no hay fotos")

    imgs = [_load_as_pil(p) for p in photos]
    n = len(imgs)
    n_slides = min(n_slides, n)

    # 1. cover
    best = photo_editor.pick_cover(imgs, fmt_key=fmt_key)
    cover_idx = best.index

    remaining = [i for i in range(n) if i != cover_idx]

    # 2. detalle: mayor sharpness entre los restantes
    detail_idx = (
        max(remaining, key=lambda i: _detail_score(imgs[i]))
        if remaining
        else cover_idx
    )
    remaining = [i for i in remaining if i != detail_idx]

    # 3. lifestyle: mejor rule_of_thirds entre los restantes
    lifestyle_idx = (
        max(remaining, key=lambda i: photo_editor._rule_of_thirds_score(imgs[i]))
        if remaining
        else detail_idx
    )
    remaining = [i for i in remaining if i != lifestyle_idx]

    # 4. cierre: mayor openness
    cierre_idx = (
        max(remaining, key=lambda i: _openness_score(imgs[i]))
        if remaining
        else lifestyle_idx
    )
    remaining = [i for i in remaining if i != cierre_idx]

    assignment = [
        (cover_idx, "apertura"),
        (detail_idx, "detalle"),
        (lifestyle_idx, "lifestyle"),
        (cierre_idx, "cierre"),
    ][:n_slides]

    curated: list[CuratedPhoto] = []
    for pos, (idx, role) in enumerate(assignment, start=1):
        curated.append(
            CuratedPhoto(
                index=idx,
                role=role,
                template=TEMPLATE_BY_ROLE.get(role, "editorial_hero"),
                slide_position=pos,
            )
        )

    logger.info(
        "curator.ready",
        extra={
            "topic": topic,
            "n_in": n,
            "n_out": len(curated),
            "cover_index": cover_idx,
        },
    )

    return CuratedSet(
        topic=topic,
        cover_index=cover_idx,
        order=curated,
        skipped_indices=remaining,
    )


def curate_to_slides(
    photos: list[Path | bytes | Image.Image],
    topic: str,
    n_slides: int = 4,
    fmt_key: str = "ig_feed_portrait",
    headlines: dict[str, str] | None = None,
) -> tuple[CuratedSet, list[SlideBrief]]:
    """Wrapper que además arma SlideBrief con template elegida y headline vacío.

    El Copywriter / Director llenará los headlines después. Si se pasan
    `headlines` con keys = role, se prellenan.
    """
    curated = curate(photos, topic, n_slides=n_slides, fmt_key=fmt_key)

    slides: list[SlideBrief] = []
    for cp in curated.order:
        headline = (headlines or {}).get(cp.role, "")
        slides.append(
            SlideBrief(
                index=cp.slide_position,
                headline=headline or f"[{cp.role}]",
                body=None,
                visual_prompt=f"REAL_PHOTO #{cp.index} — role={cp.role}",
                template=cp.template,
            )
        )
    return curated, slides
