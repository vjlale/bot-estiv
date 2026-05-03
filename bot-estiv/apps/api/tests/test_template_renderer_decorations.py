"""Tests de las decoraciones nuevas del template_renderer:
dimension_line, numbered_badge, callout_panel.

No validan píxeles exactos — validan que el render no crashea, respeta bbox
y que ciertos píxeles esperados cambiaron (fondo vs dibujado)."""
from __future__ import annotations

import io

from PIL import Image

from bot_estiv.tools import template_renderer as tr


def _canvas_with_decos(decos: list[tr.Decoration], bg: str = "#FFFFFF") -> Image.Image:
    spec = tr.TemplateSpec(
        name="t", size=(400, 300),
        slots={"image": tr.Slot(bbox=(0, 0, 400, 300), fit="cover")},
        decorations=decos,
        background_color=bg,
    )
    img = Image.new("RGB", (400, 300), bg)
    png = tr.render(spec=spec, values={"image": img})
    return Image.open(io.BytesIO(png)).convert("RGB")


def test_dimension_line_horizontal_draws_pixels():
    deco = tr.Decoration(
        type="dimension_line",
        bbox=(50, 150, 350, 154),
        orientation="h",
        fill="#000000",
        weight=3,
        tick_len=10,
        label="test",
    )
    out = _canvas_with_decos([deco])
    # pixel sobre la línea (y~=152) debe ser oscuro
    r, g, b = out.getpixel((200, 152))
    assert r + g + b < 200
    # pixel muy arriba (y=10) debe ser fondo
    r2, g2, b2 = out.getpixel((200, 10))
    assert r2 + g2 + b2 > 700


def test_dimension_line_vertical_ticks():
    deco = tr.Decoration(
        type="dimension_line",
        bbox=(200, 50, 204, 250),
        orientation="v",
        fill="#000000",
        weight=3,
        tick_len=14,
    )
    out = _canvas_with_decos([deco])
    # tick en el extremo superior (y=50, x≈202) → negro
    r, g, b = out.getpixel((202, 52))
    assert r + g + b < 200


def test_numbered_badge_draws_circle_and_number():
    deco = tr.Decoration(
        type="numbered_badge",
        bbox=(180, 130, 220, 170),
        number=5,
        radius=20,
        fill="#336699",
        text_color="#FFFFFF",
    )
    out = _canvas_with_decos([deco])
    # un punto al borde del círculo (cerca del fill, no del número blanco)
    # el círculo tiene radio 20 centrado en (200,150). Sampleo en (188, 150) → dentro del fill
    edge = out.getpixel((188, 150))
    # no puede ser blanco (fondo) — debe ser el fill azul aproximado
    assert edge[2] > edge[0], f"expected blueish, got {edge}"


def test_numbered_badge_with_lead_line():
    """Dibuja lead-line desde el badge a otro punto — pixel de la linea debe
    estar coloreado."""
    deco = tr.Decoration(
        type="numbered_badge",
        bbox=(50, 130, 90, 170),
        number=1,
        radius=20,
        fill="#FF0000",
        text_color="#FFFFFF",
        weight=3,
        line_to=(350, 150),
    )
    out = _canvas_with_decos([deco])
    # en medio de la línea debe haber rojo
    r, g, b = out.getpixel((200, 150))
    assert r > 150 and g < 100 and b < 100


def test_callout_panel_renders_title_and_body():
    deco = tr.Decoration(
        type="callout_panel",
        bbox=(30, 30, 370, 270),
        fill="#EEEEEE",
        opacity=1.0,
        panel_radius=8,
        panel_padding=20,
        panel_title="Title aqui",
        panel_body="Body detallado del callout panel para validar wrap",
        label_font_size_px=18,
    )
    out = _canvas_with_decos([deco])
    # dentro del panel debe haber pixeles grises del fill
    r, g, b = out.getpixel((40, 40))
    assert 200 < r < 250
    # fuera del panel debe ser fondo blanco
    r2, g2, b2 = out.getpixel((10, 10))
    assert r2 + g2 + b2 > 700


def test_decoration_from_dict_bbox_and_line_to_tuple():
    """_spec_from_dict debe convertir list→tuple en bbox y line_to."""
    spec_dict = {
        "name": "json_test",
        "size": [400, 300],
        "slots": {},
        "decorations": [
            {
                "type": "numbered_badge",
                "bbox": [100, 100, 140, 140],
                "number": 7,
                "radius": 20,
                "fill": "#000000",
                "line_to": [300, 200],
            }
        ],
    }
    spec = tr._spec_from_dict(spec_dict)
    assert spec.decorations[0].bbox == (100, 100, 140, 140)
    assert spec.decorations[0].line_to == (300, 200)
    assert spec.decorations[0].number == 7


def test_all_new_decos_together_no_crash():
    decos = [
        tr.Decoration(type="dimension_line", bbox=(50, 30, 350, 34),
                      orientation="h", fill="#000000", weight=2, tick_len=8, label="Dim"),
        tr.Decoration(type="numbered_badge", bbox=(30, 100, 70, 140),
                      number=1, radius=20, fill="#5F8575", text_color="#FFF",
                      line_to=(150, 120)),
        tr.Decoration(type="callout_panel", bbox=(180, 100, 370, 250),
                      fill="#F5F1EA", opacity=0.95, panel_title="Hola",
                      panel_body="mundo", label_font_size_px=16),
    ]
    out = _canvas_with_decos(decos, bg="#FFFFFF")
    assert out.size == (400, 300)
