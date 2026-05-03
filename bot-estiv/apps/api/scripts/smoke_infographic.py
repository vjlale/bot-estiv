"""Smoke end-to-end de las 2 plantillas infográficas (contra Gemini real).

Caso 1: mesa con dimensiones (2,20 m × 76 cm) usando `infographic_dimensions`
Caso 2: cerco con 3 pasos usando `numbered_steps`

Uso:
    uv run python scripts/smoke_infographic.py [--only dimensions|steps]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from bot_estiv.agents import brand_guardian, content_designer  # noqa: E402
from bot_estiv.schemas import (  # noqa: E402
    DesignBrief,
    DimensionSpec,
    InfographicData,
    SlideBrief,
    StepItem,
)


def banner(msg: str) -> None:
    print("\n" + "=" * 72)
    print(msg)
    print("=" * 72)


async def run_dimensions() -> str:
    banner("[1] infographic_dimensions — mesa Quebracho 2,20 m")
    brief = DesignBrief(
        format="ig_feed_portrait",  # será reemplazado por el target nativo 1920x1080
        pillar="durabilidad",
        content_type="educativo",
        topic=(
            "Mesa de jardín de quebracho macizo con ensambles artesanales, "
            "pieza central de una galería exterior"
        ),
        slides=[
            SlideBrief(
                index=1,
                headline="Dimensiones concebidas para dominar el espacio",
                visual_prompt="quebracho table isolated on bone background, 3/4 perspective",
            )
        ],
        infographic_data=InfographicData(
            dimensions=[
                DimensionSpec(value_cm=220, label="2,20 metros de largo", axis="horizontal"),
                DimensionSpec(
                    value_cm=76,
                    label="76 centímetros\nde ancho\n(aproximadamente)",
                    axis="vertical",
                ),
            ],
            description=(
                "Más que un mueble: es una pieza constructiva y escultural "
                "fabricada íntegramente en madera dura, diseñada para anclar "
                "el diseño de cualquier ambiente exterior."
            ),
            project_label="Una pieza constructiva",
        ),
    )
    t0 = time.time()
    urls = await content_designer.generate_infographic_post(brief)
    print(f"ok {time.time() - t0:.1f}s → {urls[0]}")
    return urls[0]


async def run_steps() -> str:
    banner("[2] numbered_steps — cerco Ingeniería Oculta")
    brief = DesignBrief(
        format="ig_feed_portrait",
        pillar="durabilidad",
        content_type="educativo",
        topic=(
            "Detalle técnico de cerco de quebracho con durmientes verticales "
            "anclados con hormigón, proyecto en jardín"
        ),
        slides=[
            SlideBrief(
                index=1,
                headline="Ingeniería oculta para máxima estabilidad",
                visual_prompt="close-up of quebracho fence posts embedded in ground, clean studio background",
            )
        ],
        infographic_data=InfographicData(
            steps=[
                StepItem(
                    number=1,
                    title="Fijación subterránea",
                    body=(
                        "Cada durmiente se entierra entre 20 y 30 cm bajo el "
                        "nivel del suelo, asegurando una base inamovible."
                    ),
                ),
                StepItem(
                    number=2,
                    title="Sistema continuo",
                    body=(
                        "Colocados exactamente uno al lado del otro, sin "
                        "fisuras, para lograr un bloque visual sólido y "
                        "privacidad total."
                    ),
                ),
                StepItem(
                    number=3,
                    title="Hormigonado individual",
                    body=(
                        "El anclaje se realiza con hormigón vertido poste por "
                        "poste, garantizando resistencia contra vientos y "
                        "movimientos de tierra."
                    ),
                ),
            ],
            project_label="Cerco Mendiolaza",
        ),
    )
    t0 = time.time()
    urls = await content_designer.generate_infographic_post(brief)
    print(f"ok {time.time() - t0:.1f}s → {urls[0]}")
    return urls[0]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["dimensions", "steps"], default=None)
    args = parser.parse_args()

    results: dict[str, str] = {}

    if args.only in (None, "dimensions"):
        results["infographic_dimensions"] = await run_dimensions()

    if args.only in (None, "steps"):
        results["numbered_steps"] = await run_steps()

    banner("Brand Guardian")
    for name, url in results.items():
        if not url.startswith("file://"):
            continue
        raw = Path(url.removeprefix("file://")).read_bytes()
        check = brand_guardian.validate_rendered_template(
            raw, template_name=name, fmt_key=None
        )
        flag = "[OK]" if check.passed else "[!!]"
        print(f"{flag} {name}: score={check.score:.2f} issues={check.issues} warns={check.warnings}")

    print("\n" + json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
