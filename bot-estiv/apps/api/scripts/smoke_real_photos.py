"""Smoke end-to-end con FOTOS REALES (sin Gemini generativa).

Genera un carrusel Gardens Wood a partir de un set de fotos locales,
aplicando:
  1. PhotoEditor (color grading + auto crop)
  2. RealPhotoCurator (roles narrativos)
  3. TemplateRenderer (overlays con Playfair + Montserrat + logo)
  4. BrandGuardian reforzado (contraste + logo + legibilidad)

Uso:
    uv run python scripts/smoke_real_photos.py --dir <carpeta_con_fotos>

Si `--dir` está vacío, usa imágenes sintéticas con gradientes tipo quebracho
para validar el pipeline.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from bot_estiv.agents import brand_guardian, real_photo_curator  # noqa: E402
from bot_estiv.agents.content_designer import generate_post_from_photos  # noqa: E402
from bot_estiv.schemas import DesignBrief  # noqa: E402
from bot_estiv.tools import template_renderer  # noqa: E402


def _synthetic_photos(n: int = 4) -> list[Image.Image]:
    """Genera imágenes sintéticas de tamaños variados tipo paleta quebracho."""
    palette = [
        ((120, 85, 55), (180, 140, 90)),
        ((60, 50, 40), (200, 170, 130)),
        ((100, 70, 50), (210, 180, 140)),
        ((80, 90, 60), (170, 190, 140)),
    ]
    imgs: list[Image.Image] = []
    sizes = [(1800, 1200), (1080, 1350), (1200, 900), (1440, 1080)]
    for i in range(n):
        w, h = sizes[i % len(sizes)]
        img = Image.new("RGB", (w, h), palette[i % len(palette)][0])
        for y in range(h):
            t = y / max(1, h - 1)
            s, e = palette[i % len(palette)]
            r = int(s[0] + (e[0] - s[0]) * t)
            g = int(s[1] + (e[1] - s[1]) * t)
            b = int(s[2] + (e[2] - s[2]) * t)
            for x in range(w):
                img.putpixel((x, y), (r, g, b))
        imgs.append(img)
    return imgs


def _load_photos(directory: Path) -> list[Image.Image]:
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in exts)
    if not paths:
        raise FileNotFoundError(f"No se encontraron imágenes en {directory}")
    return [Image.open(p).convert("RGB") for p in paths]


def banner(msg: str) -> None:
    print("\n" + "=" * 72)
    print(msg)
    print("=" * 72)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", help="Carpeta con fotos reales de la obra")
    parser.add_argument("--project", default="cerco-mendiolaza", help="project_tag")
    parser.add_argument("--topic", default="Cerco de quebracho 30 metros lineales en Mendiolaza")
    parser.add_argument(
        "--headlines-json",
        help="JSON opcional con headlines por role, ej "
        '{"apertura":"Cerco de 30m","detalle":"Cada tabla, una vida"}',
    )
    args = parser.parse_args()

    banner("BOT ESTIV — smoke de FOTOS REALES (sin Gemini)")
    if args.dir:
        photos = _load_photos(Path(args.dir))
        print(f"Cargadas {len(photos)} fotos desde {args.dir}")
    else:
        photos = _synthetic_photos()
        print("Usando fotos SINTÉTICAS (no se pasó --dir)")

    headlines = {
        "apertura": "Cerco de quebracho · 30 metros",
        "detalle": "La nobleza del quebracho en cada tabla",
        "lifestyle": "Un límite que se vuelve arquitectura",
        "cierre": "Diseñado para perdurar generaciones",
    }
    if args.headlines_json:
        headlines.update(json.loads(args.headlines_json))

    # 1. Curación
    banner("[1/4] RealPhotoCurator — roles narrativos")
    curated, slides = real_photo_curator.curate_to_slides(
        photos,
        topic=args.topic,
        n_slides=min(4, len(photos)),
        fmt_key="ig_feed_portrait",
        headlines=headlines,
    )
    print(f"cover idx={curated.cover_index}  | skipped={curated.skipped_indices}")
    for cp in curated.order:
        print(f"  slide {cp.slide_position}: photo#{cp.index} · {cp.role} · {cp.template}")

    # 2. Render con pipeline de fotos reales
    banner("[2/4] ContentDesigner.generate_post_from_photos")
    brief = DesignBrief(
        format="carousel_portrait",
        pillar="durabilidad",
        content_type="promocional",
        topic=args.topic,
        slides=slides,
    )
    mapping = [cp.index for cp in curated.order]
    urls = await generate_post_from_photos(photos, brief, photo_indices_by_slide=mapping)
    for i, u in enumerate(urls, 1):
        print(f"  slide {i} → {u}")

    # 3. Brand Guardian por cada slide
    banner("[3/4] BrandGuardian (contrast + legibility + logo)")
    checks: list[dict] = []
    for i, (u, cp) in enumerate(zip(urls, curated.order), 1):
        if not u.startswith("file://"):
            continue
        raw = Path(u.removeprefix("file://")).read_bytes()
        result = brand_guardian.validate_rendered_template(
            raw, template_name=cp.template, fmt_key="carousel_portrait"
        )
        checks.append({"slide": i, "template": cp.template, **result.model_dump()})
        flag = "✓" if result.passed else "✗"
        print(
            f"  slide {i} [{cp.template}]: {flag} passed={result.passed} "
            f"score={result.score:.2f} issues={result.issues} warns={result.warnings}"
        )

    # 4. Resumen
    banner("[4/4] Resultado")
    summary = {
        "project": args.project,
        "topic": args.topic,
        "slides": [
            {
                "position": cp.slide_position,
                "photo_index": cp.index,
                "role": cp.role,
                "template": cp.template,
            }
            for cp in curated.order
        ],
        "assets": urls,
        "brand_checks": checks,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
