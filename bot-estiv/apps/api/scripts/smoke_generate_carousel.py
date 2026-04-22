"""Smoke test: genera un CARRUSEL completo (copy + N imágenes) con el stack Gemini.

Uso:
    uv run python scripts/smoke_generate_carousel.py

Pasos:
  1. Copywriter → title/caption/hashtags/cta del post principal
  2. CarouselPlanner → N SlideBrief (ángulos visuales distintos)
  3. ContentDesigner → N imágenes Nano Banana 2 con overlay tipográfico y logo
  4. BrandGuardian → validación de copy e imágenes
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from bot_estiv.agents import (  # noqa: E402
    brand_guardian,
    carousel_planner,
    content_designer,
    copywriter,
)
from bot_estiv.schemas import DesignBrief  # noqa: E402


TOPIC = "Pérgolas de Quebracho: cómo transforman un patio en un espacio de encuentro"
PILLAR = "diseno"
CONTENT_TYPE = "educativo"
FORMAT = "carousel_portrait"  # 1080x1350
N_SLIDES = 4


def banner(msg: str) -> None:
    print("\n" + "=" * 70)
    print(msg)
    print("=" * 70)


async def main() -> None:
    banner(f"BOT ESTIV — carousel smoke test  ({N_SLIDES} slides)")
    print(f"Topic:  {TOPIC}")
    print(f"Pillar: {PILLAR}")
    print(f"Format: {FORMAT}")

    # ---------- 1. Copy ----------
    banner("[1/4] Copywriter — Gemini 3.1 Flash Lite")
    t0 = time.time()
    copy = await copywriter.run(TOPIC, pillar=PILLAR, content_type=CONTENT_TYPE)
    print(f"ok en {time.time() - t0:.1f}s")
    print(f"  title  : {copy.title}")
    print(f"  caption: {copy.caption[:140]}…")
    print(f"  hashtags: {len(copy.hashtags)} → {' '.join(copy.hashtags[:8])}…")

    # ---------- 2. Carousel plan ----------
    banner("[2/4] CarouselPlanner — plan de slides")
    t0 = time.time()
    slides = await carousel_planner.run(TOPIC, n_slides=N_SLIDES)
    print(f"ok en {time.time() - t0:.1f}s — {len(slides)} slides")
    for s in slides:
        print(f"  [{s.index}] {s.headline}")
        print(f"       body   : {(s.body or '—')[:80]}")
        print(f"       visual : {s.visual_prompt[:110]}…")

    # ---------- 3. Generación de imágenes ----------
    banner("[3/4] ContentDesigner — Nano Banana 2 ×N")
    brief = DesignBrief(
        format=FORMAT,
        pillar=PILLAR,
        content_type=CONTENT_TYPE,
        topic=TOPIC,
        slides=slides,
    )
    t0 = time.time()
    urls = await content_designer.generate_post(brief)
    print(f"ok en {time.time() - t0:.1f}s")
    for i, u in enumerate(urls, 1):
        print(f"  slide {i} → {u}")

    # ---------- 4. Brand Guardian ----------
    banner("[4/4] BrandGuardian")
    copy_check = brand_guardian.validate_copy(copy)
    print(
        f"  copy   → passed={copy_check.passed} score={copy_check.score:.2f} "
        f"issues={copy_check.issues} warns={copy_check.warnings}"
    )
    img_checks: list[dict] = []
    for i, u in enumerate(urls, 1):
        if u.startswith("file://"):
            raw = Path(u.removeprefix("file://")).read_bytes()
            c = brand_guardian.validate_image(raw, fmt_key=FORMAT)
            img_checks.append({"slide": i, **c.model_dump()})
            flag = "✓" if c.passed else "✗"
            print(
                f"  img {i}  → {flag} passed={c.passed} score={c.score:.2f} "
                f"warns={c.warnings} issues={c.issues}"
            )

    banner("RESULTADO")
    print(
        json.dumps(
            {
                "copy": copy.model_dump(),
                "slides": [s.model_dump() for s in slides],
                "assets": urls,
                "brand_check_copy": copy_check.model_dump(),
                "brand_check_images": img_checks,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
