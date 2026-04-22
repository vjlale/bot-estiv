"""PhotoEditor — procesa fotos REALES de obras sin alterarlas con AI.

Tres pasos:
1. `color_grade_gw(img)` aplica una LUT de marca (warm/quebracho, sombras
   cálidas, medios con contraste suave, greens levemente desaturados).
2. `auto_crop(img, fmt)` recorta al formato destino usando una heurística
   simple de energía de imagen (regla de tercios → centro de masa horizontal).
3. `pick_cover(imgs)` elige la foto más pro para portada (sharpness +
   regla de tercios + cercanía al ratio destino).

NO usa AI generativa. La foto real queda real.
"""
from __future__ import annotations

import io
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from ..brand import FORMATS

logger = logging.getLogger(__name__)


# ========== Color grading ==========


def _apply_rgb_curves(img: Image.Image) -> Image.Image:
    """Aplica curvas de canal para un look cálido Gardens Wood.

    - Shadows: un poco más cálidas (+R, -B)
    - Mids: ligero contraste
    - Highlights: protegidos, apenas un toque ámbar

    Implementación con LUTs 256 por canal via Image.point.
    """

    def curve_r(v: int) -> int:
        # sombras más cálidas, highlights casi intactos
        if v < 64:
            return min(255, int(v * 1.18))
        if v < 160:
            return int(v * 1.06)
        return min(255, int(v * 1.02))

    def curve_g(v: int) -> int:
        # greens desaturados sutilmente para evitar pastos verdes chillones
        return int(v * 0.97)

    def curve_b(v: int) -> int:
        # menos azul en sombras (warm), neutro en highlights
        if v < 80:
            return int(v * 0.85)
        if v < 180:
            return int(v * 0.95)
        return v

    r, g, b = img.convert("RGB").split()
    r = r.point([curve_r(i) for i in range(256)])
    g = g.point([curve_g(i) for i in range(256)])
    b = b.point([curve_b(i) for i in range(256)])
    return Image.merge("RGB", (r, g, b))


def color_grade_gw(img: Image.Image, strength: float = 1.0) -> Image.Image:
    """Aplica el look Gardens Wood a una imagen.

    `strength ∈ [0, 1]` controla la intensidad; 1.0 es full look.
    """
    base = img.convert("RGB")

    graded = _apply_rgb_curves(base)

    # blend para controlar strength
    if strength < 1.0:
        graded = Image.blend(base, graded, strength)

    # contraste fino + saturación dando dignidad
    graded = ImageEnhance.Contrast(graded).enhance(1 + 0.08 * strength)
    graded = ImageEnhance.Color(graded).enhance(1 - 0.05 * strength)
    graded = ImageEnhance.Brightness(graded).enhance(1 + 0.02 * strength)

    return graded


# ========== Auto-crop a formato ==========


def _energy_map(img: Image.Image) -> Image.Image:
    """Mapa de energía simple: magnitud de gradiente en escala de grises."""
    gray = img.convert("L")
    # bordes para detectar detalle/textura
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # suavizar un toque para evitar dominar por ruido
    return edges.filter(ImageFilter.BoxBlur(radius=8))


def _center_of_mass(energy: Image.Image) -> tuple[float, float]:
    """Centro de masa (normalizado a [0,1]) del mapa de energía."""
    w, h = energy.size
    pixels = energy.getdata()
    total = 0
    sx = 0.0
    sy = 0.0
    for idx, v in enumerate(pixels):
        x = idx % w
        y = idx // w
        total += v
        sx += x * v
        sy += y * v
    if total == 0:
        return (0.5, 0.5)
    return (sx / total / w, sy / total / h)


def auto_crop(img: Image.Image, fmt_key: str) -> Image.Image:
    """Recorta `img` al aspect ratio de `fmt_key` centrando el recorte en
    el centro de masa de la energía de imagen (rule-of-thirds friendly).
    """
    if fmt_key not in FORMATS:
        raise ValueError(f"Formato desconocido: {fmt_key}")
    target_w, target_h = FORMATS[fmt_key]
    target_ratio = target_w / target_h

    sw, sh = img.size
    src_ratio = sw / sh

    if abs(src_ratio - target_ratio) < 0.01:
        # mismo ratio: solo resize
        return img.resize((target_w, target_h), Image.LANCZOS)

    # downsample para calcular energía rápido
    work = img.copy()
    work.thumbnail((400, 400))
    cx_norm, cy_norm = _center_of_mass(_energy_map(work))

    # Calculamos el crop manteniendo ratio target
    if src_ratio > target_ratio:
        # muy ancha: recortar a los lados
        new_w = int(sh * target_ratio)
        new_h = sh
        cx = int(cx_norm * sw)
        left = max(0, min(sw - new_w, cx - new_w // 2))
        top = 0
    else:
        # muy alta: recortar arriba/abajo
        new_w = sw
        new_h = int(sw / target_ratio)
        cy = int(cy_norm * sh)
        top = max(0, min(sh - new_h, cy - new_h // 2))
        left = 0

    cropped = img.crop((left, top, left + new_w, top + new_h))
    return cropped.resize((target_w, target_h), Image.LANCZOS)


# ========== Pick cover ==========


@dataclass
class PhotoScore:
    index: int
    sharpness: float
    rule_of_thirds: float
    aspect_match: float
    total: float


def _sharpness(img: Image.Image) -> float:
    """Varianza del Laplaciano aproximado (medida de foco/enfoque)."""
    gray = img.convert("L")
    small = gray.copy()
    small.thumbnail((640, 640))
    # Laplaciano: sharpness = var(pixeles de bordes)
    edges = small.filter(ImageFilter.FIND_EDGES)
    pixels = list(edges.getdata())
    n = len(pixels)
    if n == 0:
        return 0.0
    mean = sum(pixels) / n
    var = sum((p - mean) ** 2 for p in pixels) / n
    return var


def _rule_of_thirds_score(img: Image.Image) -> float:
    """Qué tan cerca está el centro de masa de una intersección de tercios."""
    small = img.copy()
    small.thumbnail((320, 320))
    cx, cy = _center_of_mass(_energy_map(small))
    # Intersecciones de tercios
    targets = [(1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3)]
    best = min(math.hypot(cx - tx, cy - ty) for tx, ty in targets)
    # invertir distancia (más cerca = mejor). max dist ≈ 0.47
    return max(0.0, 1.0 - best / 0.47)


def _aspect_match_score(img: Image.Image, fmt_key: str) -> float:
    """1.0 si el ratio ya coincide, baja con la diferencia."""
    target_w, target_h = FORMATS[fmt_key]
    target_ratio = target_w / target_h
    src_ratio = img.width / img.height
    diff = abs(src_ratio - target_ratio) / target_ratio
    return max(0.0, 1.0 - diff)


def pick_cover(imgs: Iterable[Image.Image], fmt_key: str = "ig_feed_portrait") -> PhotoScore:
    """Elige la foto que mejor funciona como portada para el formato destino."""
    imgs = list(imgs)
    if not imgs:
        raise ValueError("pick_cover: no hay imágenes")

    scores: list[PhotoScore] = []
    max_sharp = 1.0
    raw_sharp: list[float] = []
    for img in imgs:
        raw_sharp.append(_sharpness(img))
    if raw_sharp:
        max_sharp = max(raw_sharp) or 1.0

    for i, img in enumerate(imgs):
        sh = raw_sharp[i] / max_sharp
        rt = _rule_of_thirds_score(img)
        am = _aspect_match_score(img, fmt_key)
        # ponderación: sharpness 0.45 + tercios 0.30 + aspect 0.25
        total = 0.45 * sh + 0.30 * rt + 0.25 * am
        scores.append(
            PhotoScore(
                index=i,
                sharpness=round(sh, 3),
                rule_of_thirds=round(rt, 3),
                aspect_match=round(am, 3),
                total=round(total, 3),
            )
        )
    best = max(scores, key=lambda s: s.total)
    logger.info(
        "photo.pick_cover",
        extra={"winner_index": best.index, "score": best.total, "n": len(imgs)},
    )
    return best


# ========== Pipeline completo (conveniencia) ==========


def process_photo(
    src: bytes | Image.Image | Path,
    fmt_key: str = "ig_feed_portrait",
    grade: bool = True,
    strength: float = 1.0,
) -> bytes:
    """Pipeline: abrir → EXIF auto-rotate → color grade → auto crop → PNG bytes."""
    if isinstance(src, (str, Path)):
        img = Image.open(Path(src))
    elif isinstance(src, bytes):
        img = Image.open(io.BytesIO(src))
    else:
        img = src

    # corrige orientación según EXIF (celulares suelen rotar virtualmente)
    img = ImageOps.exif_transpose(img).convert("RGB")

    if grade:
        img = color_grade_gw(img, strength=strength)

    img = auto_crop(img, fmt_key)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
