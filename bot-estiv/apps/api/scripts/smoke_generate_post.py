"""Smoke test end-to-end: genera un post completo con el stack Gemini.

Uso:
    uv run python scripts/smoke_generate_post.py

Produce:
- Copy (title + caption + hashtags + cta)
- Imagen generada por Nano Banana 2 + canvas_design.finalize (logo + overlay)
- Brand check automático
- Archivo local en `media_local/posts/...`
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from bot_estiv.agents import brand_guardian, content_designer, copywriter  # noqa: E402
from bot_estiv.schemas import DesignBrief  # noqa: E402


TOPIC = "Mesas de Quebracho macizo para jardín: cómo sobreviven 30 años a la intemperie"
PILLAR = "durabilidad"
CONTENT_TYPE = "educativo"
FORMAT = "ig_feed_portrait"


async def main() -> None:
    print("=" * 70)
    print("BOT ESTIV — smoke test end-to-end (Gemini-only)")
    print("=" * 70)
    print(f"Topic:   {TOPIC}")
    print(f"Pillar:  {PILLAR}")
    print(f"Format:  {FORMAT}\n")

    # ---------- 1. Copywriter ----------
    print("[1/3] Copywriter (Gemini 3.1 Flash Lite)…")
    t0 = time.time()
    copy = await copywriter.run(TOPIC, pillar=PILLAR, content_type=CONTENT_TYPE)
    print(f"    ok en {time.time() - t0:.1f}s")
    print(f"    title  : {copy.title}")
    print(f"    caption: {copy.caption[:140]}…")
    print(f"    tags   : {len(copy.hashtags)} → {' '.join(copy.hashtags[:8])}…")
    print(f"    cta    : {copy.cta}\n")

    # ---------- 2. ContentDesigner + Nano Banana 2 ----------
    print("[2/3] ContentDesigner (Nano Banana 2 + canvas_design)…")
    brief = DesignBrief(
        format=FORMAT,
        pillar=PILLAR,
        content_type=CONTENT_TYPE,
        topic=TOPIC,
        slides=[],
    )
    t0 = time.time()
    urls = await content_designer.generate_post(brief)
    print(f"    ok en {time.time() - t0:.1f}s")
    for u in urls:
        print(f"    → {u}")
    print()

    # ---------- 3. Brand Guardian ----------
    print("[3/3] BrandGuardian (reglas de marca)…")
    t0 = time.time()
    check = brand_guardian.validate_copy(copy)
    # Validación de imagen: leer el primer archivo local generado
    img_check = None
    first = urls[0]
    if first.startswith("file://"):
        raw = Path(first.removeprefix("file://")).read_bytes()
        img_check = brand_guardian.validate_image(raw, fmt_key=FORMAT)
    print(f"    ok en {time.time() - t0:.1f}s")
    print(f"    copy   → passed={check.passed} score={check.score:.2f}")
    if check.issues:
        print(f"            issues : {check.issues}")
    if check.warnings:
        print(f"            warns  : {check.warnings}")
    if img_check:
        print(
            f"    image  → passed={img_check.passed} score={img_check.score:.2f} "
            f"warnings={img_check.warnings} issues={img_check.issues}"
        )

    print("\n" + "=" * 70)
    print("RESULTADO COMPLETO")
    print("=" * 70)
    print(
        json.dumps(
            {
                "copy": copy.model_dump(),
                "assets": urls,
                "brand_check_copy": check.model_dump(),
                "brand_check_image": img_check.model_dump() if img_check else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
