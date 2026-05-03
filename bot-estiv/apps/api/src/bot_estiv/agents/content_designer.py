"""ContentDesigner: genera piezas visuales (posts, stories, carruseles).

Flujo:
1. Dado un DesignBrief, produce N prompts visuales consistentes con marca.
2. Llama a Gemini 3.1 Flash Image (Nano Banana 2) para generar la imagen base.
3. Pasa el resultado por canvas_design.finalize() para respetar formato, logo y overlay.
4. Sube a storage y devuelve URLs.
"""
from __future__ import annotations

import asyncio
import logging

from pathlib import Path

from PIL import Image

from ..brand import CATALOG, FORMATS, PALETTE, VOICE
from ..rag import retrieve_brand_context
from ..schemas import DesignBrief, SlideBrief
from ..tools import canvas_design, image_gen, photo_editor, storage, template_renderer


# Mapa de rol narrativo → plantilla por defecto para carruseles (posición 1-based).
# Para quote_card y before_after asignar via SlideBrief.template explícitamente.
# Ver skills/graphic-designer/SKILL.md para la guía completa de selección.
_ROLE_TEMPLATE_BY_INDEX = {
    1: "cover_hero",      # apertura impactante
    2: "minimal_stamp",   # detalle de artesanía / respiro visual
    3: "editorial_hero",  # lifestyle con copy narrativo
    4: "split_60_40",     # información / proceso / dato técnico
    5: "spec_card",       # ficha técnica o cierre con datos
}

logger = logging.getLogger(__name__)


STYLE_ANCHOR = (
    "Photographic style inspired by premium outdoor design magazines. "
    "Argentine quebracho wood in warm golden-hour light. "
    f"Mood palette: deep charcoal {PALETTE.gris_carbon}, bone white {PALETTE.blanco_hueso}, "
    f"quebracho brown {PALETTE.marron_quebracho}, eucalyptus green {PALETTE.verde_eucalipto}, "
    f"fire orange accent {PALETTE.naranja_fuego}. "
    "Selective focus on wood grain and joinery. Human presence subtle and indirect. "
    "Natural, elegant, serene, never kitsch."
    f"\n\nGardens Wood ONLY manufactures: {CATALOG.products_str()}. "
    f"Materials used: {', '.join(CATALOG.materials)}. "
    f"STRICTLY FORBIDDEN to depict any of these (not in the catalog): "
    f"{CATALOG.forbidden_str()}. "
    "If the topic suggests something outside the catalog, reframe the scene to use "
    "products from the catalog that fit the narrative."
)


def build_visual_prompt(topic: str, slide: SlideBrief | None = None) -> str:
    subject = slide.visual_prompt if slide and slide.visual_prompt else topic
    parts = [subject, STYLE_ANCHOR]
    if slide and slide.headline:
        parts.append(
            f"Leave clean negative space at the bottom for a typographic overlay "
            f"with the phrase: '{slide.headline}'. Do NOT render text in the image."
        )
    else:
        parts.append("Leave clean negative space for typographic overlay; no text in image.")
    return " ".join(parts)


def build_clean_infographic_prompt(topic: str, template_name: str) -> str:
    """Prompt especializado para bases de infografías: producto aislado, SIN texto,
    sin dimensiones ni labels dibujadas, con mucho negative space para que Pillow
    compoga encima los callouts, dimension lines, badges y textos reales.

    `template_name` ajusta hints de composición según la plantilla destino
    (infographic_dimensions vs numbered_steps).
    """
    layout_hint = (
        "Product centered horizontally, photographed from a slight 3/4 perspective "
        "on a seamless bone-white background, studio editorial lighting. "
        "Keep 40% negative space above and to the right and bottom of the product."
        if template_name == "infographic_dimensions"
        else (
            "Product or scene centered vertically in the frame, isolated on a "
            "light neutral background. Keep a wide margin of 30% on both left and "
            "right sides so numbered callouts and description panels can be placed "
            "outside the product zone without overlapping."
        )
    )
    return (
        f"Editorial product photograph for a technical infographic about: {topic}.\n\n"
        f"{layout_hint}\n\n"
        "STYLE: Premium outdoor design magazine aesthetic. Quebracho wood visible. "
        "Warm golden-hour ambient but clean shadows, high dynamic range, sharp "
        "details on wood grain and joinery. Eucalyptus green and orange accents "
        "only if naturally present, never as graphic shapes.\n\n"
        f"{STYLE_ANCHOR}\n\n"
        "CRITICAL — IMAGE MUST BE COMPLETELY CLEAN OF GRAPHIC OVERLAYS:\n"
        "- DO NOT render ANY text, numbers, letters, dimensions, labels, legends, "
        "captions, watermarks, arrows, callouts, badges, circles with numbers, "
        "measuring lines, rulers, diagrams, coordinate axes or data-viz elements.\n"
        "- DO NOT draw measuring tape, dimension arrows, ruler marks, or technical "
        "annotations. I will compose those graphically on top of the image "
        "afterwards in Python using Pillow.\n"
        "- The image should look like a single product photograph, not an already "
        "composed infographic. No text of any kind anywhere in the pixels."
    )


def _pick_template(slide: SlideBrief | None, default: str, position_1based: int) -> str:
    if slide and slide.template:
        return slide.template
    return _ROLE_TEMPLATE_BY_INDEX.get(position_1based, default)


def _pillar_tag_text(pillar: str | None) -> str | None:
    if not pillar:
        return None
    return VOICE.pillars.get(pillar, pillar).split(".")[0]


async def _generate_one(
    fmt_key: str,
    topic: str,
    slide: SlideBrief | None,
    headline_overlay: str | None,
    subtitle_overlay: str | None,
    template_name: str,
    pillar: str | None = None,
) -> bytes:
    w, h = FORMATS[fmt_key]
    prompt = build_visual_prompt(topic, slide)
    raw_image = await asyncio.to_thread(image_gen.generate, prompt, w, h)
    # Pre-ajuste al formato exacto antes de overlay
    from PIL import Image as _PIL
    import io as _io

    base_img = canvas_design.fit_to_format(
        _PIL.open(_io.BytesIO(raw_image)).convert("RGB"), fmt_key
    )

    pillar_label = _pillar_tag_text(pillar) if pillar else None

    return template_renderer.render(
        spec=template_name,
        values={
            "image": base_img,
            "title": headline_overlay,
            "subtitle": subtitle_overlay,
            "pillar_tag": pillar_label,
        },
        target_size=(w, h),
    )


async def generate_post(brief: DesignBrief) -> list[str]:
    """Genera las imágenes y devuelve URLs públicas."""
    await retrieve_brand_context(brief.topic)  # warm up / grounding (side-effect)

    fmt_key = brief.format if brief.format in FORMATS else "ig_feed_portrait"
    # carrusel → portrait para IG feed (no horizontal)
    if fmt_key.startswith("carousel") or fmt_key == "ig_feed_portrait":
        fmt_key = "carousel_portrait"

    results: list[bytes] = []
    templates_used: list[str] = []

    if brief.slides:
        for i, slide in enumerate(brief.slides, start=1):
            tpl = _pick_template(slide, brief.default_template, i)
            templates_used.append(tpl)
            png = await _generate_one(
                fmt_key=fmt_key,
                topic=brief.topic,
                slide=slide,
                headline_overlay=slide.headline,
                subtitle_overlay=slide.body,
                template_name=tpl,
                pillar=brief.pillar,
            )
            results.append(png)
    else:
        tpl = brief.default_template
        templates_used.append(tpl)
        png = await _generate_one(
            fmt_key=fmt_key,
            topic=brief.topic,
            slide=None,
            headline_overlay=None,
            subtitle_overlay=None,
            template_name=tpl,
            pillar=brief.pillar,
        )
        results = [png]

    urls: list[str] = []
    for i, png in enumerate(results):
        key = storage.new_key(f"posts/{fmt_key}", "png")
        url = storage.upload_bytes(png, key, content_type="image/png")
        logger.info(
            "designer.slide_ready",
            extra={"index": i, "url": url, "template": templates_used[i]},
        )
        urls.append(url)
    return urls


# ==========  Pipeline para FOTOS REALES (sin AI generativa)  ==========


async def generate_post_from_photos(
    photos: list[Path | bytes | Image.Image],
    brief: DesignBrief,
    photo_indices_by_slide: list[int] | None = None,
) -> list[str]:
    """Arma un carrusel usando FOTOS REALES (no Nano Banana).

    Cada foto pasa por:
      1. color_grade_gw  (look Gardens Wood)
      2. auto_crop       (al formato destino)
      3. template_renderer con la plantilla elegida por la slide

    `photo_indices_by_slide` mapea posición del carrusel → index del set original.
    Si es None, usa las fotos en el orden recibido (1:1).
    """
    fmt_key = brief.format if brief.format in FORMATS else "ig_feed_portrait"
    if fmt_key.startswith("carousel") or fmt_key == "ig_feed_portrait":
        fmt_key = "carousel_portrait"

    w, h = FORMATS[fmt_key]
    pillar_label = _pillar_tag_text(brief.pillar) if brief.pillar else None

    # Cargar + EXIF-rotar todas
    from PIL import Image as _PIL
    from PIL import ImageOps as _ImageOps
    import io as _io

    def _open(src: Path | bytes | Image.Image) -> Image.Image:
        if isinstance(src, Image.Image):
            img = src
        elif isinstance(src, bytes):
            img = _PIL.open(_io.BytesIO(src))
        else:
            img = _PIL.open(Path(src))
        return _ImageOps.exif_transpose(img).convert("RGB")

    loaded = [_open(p) for p in photos]
    results: list[bytes] = []
    templates_used: list[str] = []

    slides = brief.slides or [
        SlideBrief(index=i, headline="", body=None, visual_prompt=f"photo_{i}")
        for i in range(1, len(loaded) + 1)
    ]

    for pos, slide in enumerate(slides, start=1):
        # index de foto para esta slide
        if photo_indices_by_slide and pos - 1 < len(photo_indices_by_slide):
            pidx = photo_indices_by_slide[pos - 1]
        else:
            pidx = min(pos - 1, len(loaded) - 1)

        src_img = loaded[pidx]
        graded = photo_editor.color_grade_gw(src_img, strength=1.0)
        cropped = photo_editor.auto_crop(graded, fmt_key)

        tpl = _pick_template(slide, brief.default_template, pos)
        templates_used.append(tpl)

        png = template_renderer.render(
            spec=tpl,
            values={
                "image": cropped,
                "title": slide.headline or None,
                "subtitle": slide.body,
                "pillar_tag": pillar_label,
            },
            target_size=(w, h),
        )
        results.append(png)

    urls: list[str] = []
    for i, png in enumerate(results):
        key = storage.new_key(f"posts/real/{fmt_key}", "png")
        url = storage.upload_bytes(png, key, content_type="image/png")
        logger.info(
            "designer.real_slide_ready",
            extra={"index": i, "url": url, "template": templates_used[i]},
        )
        urls.append(url)
    return urls


# ==========  Pipeline INFOGRAFÍAS (NB2 clean + plantilla rica) ==========


_DEFAULT_DESC_TITLE = "Una pieza constructiva"


async def generate_infographic_post(brief: "DesignBrief") -> list[str]:
    """Genera una pieza infográfica (dimensions o numbered_steps).

    Requiere `brief.infographic_data` populado:
      - si tiene `dimensions` → usa template `infographic_dimensions`
      - si tiene `steps` → usa template `numbered_steps`

    El fondo (producto/escena) lo genera Nano Banana 2 con un prompt CLEAN
    que instruye no dibujar texto. Pillow compone encima las dimensiones,
    badges, panels y labels con datos reales.
    """
    data = brief.infographic_data
    if data is None:
        raise ValueError(
            "generate_infographic_post requiere brief.infographic_data cargado"
        )

    # Decide template
    if data.dimensions:
        template_name = "infographic_dimensions"
    elif data.steps:
        template_name = "numbered_steps"
    else:
        raise ValueError("infographic_data sin dimensions ni steps")

    spec = template_renderer.load_template(template_name)
    target_w, target_h = spec.size

    # 1) Generar base con NB2 clean (sin texto)
    prompt = build_clean_infographic_prompt(brief.topic, template_name)
    raw = await asyncio.to_thread(image_gen.generate, prompt, target_w, target_h)
    # cargar como PIL Image
    from PIL import Image as _PIL
    import io as _io

    base_img = _PIL.open(_io.BytesIO(raw)).convert("RGB")

    # 2) Armar `values` según template
    values: dict[str, object] = {
        "image": base_img,
        "title": _pick_title_from_topic_and_data(brief, data, template_name),
    }

    if template_name == "infographic_dimensions":
        # toma la primera dimensión horizontal y la primera vertical
        h_dim = next((d for d in data.dimensions if d.axis == "horizontal"), None)
        v_dim = next((d for d in data.dimensions if d.axis == "vertical"), None)
        if h_dim:
            values["dim_top_label"] = h_dim.label
        if v_dim:
            values["dim_right_label"] = v_dim.label
        values["description_title"] = (data.project_label or _DEFAULT_DESC_TITLE).upper()
        values["description_body"] = data.description or ""
    else:  # numbered_steps
        for step in data.steps[:3]:
            values[f"step_{step.number}_title"] = step.title
            values[f"step_{step.number}_body"] = step.body

    # 3) Render
    png = template_renderer.render(
        spec=template_name,
        values=values,
        target_size=(target_w, target_h),
    )

    # 4) Storage
    key = storage.new_key(f"posts/infographic/{template_name}", "png")
    url = storage.upload_bytes(png, key, content_type="image/png")
    logger.info(
        "designer.infographic_ready",
        extra={"template": template_name, "url": url},
    )
    return [url]


def _pick_title_from_topic_and_data(
    brief: "DesignBrief",
    data,
    template_name: str,
) -> str:
    """Heurística simple para el título de la pieza. Si el brief trae un
    slide con headline, se usa. Si no, se arma algo desde el topic."""
    if brief.slides and brief.slides[0].headline:
        return brief.slides[0].headline
    if template_name == "infographic_dimensions":
        return "Dimensiones concebidas para dominar el espacio"
    return "Ingeniería oculta para máxima estabilidad"
