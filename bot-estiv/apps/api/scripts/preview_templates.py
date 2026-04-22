"""Preview rápido de las 5 plantillas sin llamar a Gemini.

Usa una imagen dummy de color sólido y aplica los overlays para ver el diseño.
Salida: preview_templates/<name>.png

Uso:
    uv run python scripts/preview_templates.py [--image <path_a_foto_real>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from bot_estiv.tools import template_renderer  # noqa: E402

SAMPLES = {
    "cover_hero": {
        "title": "Pérgolas de Quebracho",
        "subtitle": "Una inversión para décadas",
        "pillar_tag": "Durabilidad",
    },
    "editorial_hero": {
        "pillar_tag": "Durabilidad",
        "title": "La nobleza del Quebracho en cada ensamble",
        "subtitle": (
            "Cada unión es el resultado de una maestría artesanal que prioriza "
            "la solidez y la honestidad del material noble."
        ),
    },
    "minimal_stamp": {
        "pillar_tag": "Experiencia",
    },
    "split_60_40": {
        "pillar_tag": "Diseño",
        "title": "Un espacio diseñado para compartir momentos",
        "subtitle": (
            "La calidez del quebracho transforma el exterior en una extensión "
            "de tu hogar. Donde la arquitectura se funde con la naturaleza y "
            "cada tarde adquiere una cadencia propia. Diseñado para perdurar "
            "generaciones."
        ),
    },
    "spec_card": {
        "pillar_tag": "Cerco 30m — Mendiolaza",
        "title": "Quebracho colorado tratado",
        "subtitle": (
            "Altura 1.80 m · 30 metros lineales · terminación natural con aceite "
            "penetrante · garantía estructural 15 años."
        ),
    },
}


def _placeholder_image(w: int = 1080, h: int = 1350) -> Image.Image:
    """Genera una imagen de fondo con bandas diagonales cálidas (tipo mock)."""
    img = Image.new("RGB", (w, h), "#2B2722")
    # gradient diagonal manual para que no sea un plano
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    for i in range(h):
        t = i / h
        r = int(60 + 80 * t)
        g = int(45 + 50 * t)
        b = int(30 + 30 * (1 - t))
        draw.line([(0, i), (w, i)], fill=(r, g, b))
    return img


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Ruta a una imagen real para usar como fondo")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[1] / "preview_templates"),
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.image:
        base_img = Image.open(args.image).convert("RGB")
    else:
        base_img = _placeholder_image()

    for tpl_name in template_renderer.list_templates():
        values = dict(SAMPLES.get(tpl_name, {}))
        values["image"] = base_img
        png = template_renderer.render(tpl_name, values, target_size=(1080, 1350))
        out = out_dir / f"{tpl_name}.png"
        out.write_bytes(png)
        print(f"  -> {out}")


if __name__ == "__main__":
    main()
