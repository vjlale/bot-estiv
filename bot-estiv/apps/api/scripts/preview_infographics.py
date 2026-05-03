"""Preview sin Gemini de las 2 plantillas infográficas nuevas."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from bot_estiv.tools import template_renderer as tr  # noqa: E402


def _placeholder_product() -> Image.Image:
    """Imagen de producto dummy con forma de mesa rectangular sobre fondo transparente."""
    img = Image.new("RGBA", (1400, 700), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # tablero (mesa)
    draw.rectangle([(120, 240), (1280, 340)], fill=(101, 67, 33, 255))
    # patas (trapezoide aproximado con rectángulos)
    draw.rectangle([(200, 340), (300, 600)], fill=(80, 55, 28, 255))
    draw.rectangle([(1100, 340), (1200, 600)], fill=(80, 55, 28, 255))
    return img


OUT = Path(__file__).resolve().parents[1] / "preview_templates"
OUT.mkdir(parents=True, exist_ok=True)


def render_dims() -> None:
    img = _placeholder_product()
    values = {
        "image": img,
        "title": "Dimensiones concebidas para dominar el espacio",
        "dim_top_label": "2,20 metros de largo",
        "dim_right_label": "76 centímetros\nde ancho\n(aproximadamente)",
        "description_title": "Una pieza constructiva",
        "description_body": (
            "Más que un mueble: es una pieza constructiva y escultural fabricada "
            "íntegramente en madera dura, diseñada para anclar el diseño de "
            "cualquier ambiente exterior."
        ),
    }
    # render con fondo hueso detrás de la imagen transparente:
    # componemos un canvas base hueso y pegamos la imagen encima antes del renderer
    png = tr.render(spec="infographic_dimensions", values=values, target_size=(1920, 1080))
    (OUT / "infographic_dimensions.png").write_bytes(png)
    print("->", OUT / "infographic_dimensions.png")


def render_steps() -> None:
    # base: imagen representando un cerco (simple)
    base = Image.new("RGBA", (600, 700), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    # 3 durmientes verticales (columna central)
    for i, x in enumerate([220, 280, 340]):
        d.rectangle([(x, 120), (x + 40, 540)], fill=(90, 55, 30, 255))
    # base de hormigón (abajo)
    d.rectangle([(150, 480), (460, 620)], fill=(180, 180, 180, 255))

    values = {
        "image": base,
        "title": "Ingeniería Oculta para Máxima Estabilidad",
        "step_1_title": "Fijación Subterránea",
        "step_1_body": (
            "Cada durmiente se entierra entre 20 y 30 cm bajo el nivel del suelo, "
            "asegurando una base inamovible."
        ),
        "step_2_title": "Sistema Continuo",
        "step_2_body": (
            "Colocados exactamente uno al lado del otro, sin fisuras, para lograr "
            "un bloque visual sólido y privacidad total."
        ),
        "step_3_title": "Hormigonado Individual",
        "step_3_body": (
            "El anclaje se realiza con hormigón vertido poste por poste, "
            "garantizando resistencia contra vientos y movimientos de tierra."
        ),
    }
    png = tr.render(spec="numbered_steps", values=values, target_size=(1920, 1080))
    (OUT / "numbered_steps.png").write_bytes(png)
    print("->", OUT / "numbered_steps.png")


if __name__ == "__main__":
    render_dims()
    render_steps()
