"""Figma REST API → specs JSON para template_renderer.

Convención en Figma:
- Un archivo contiene frames de 1080×1350 nombrados `template:<name>`
  (ej: `template:editorial_hero`, `template:split_60_40`, etc.)
- Dentro del frame, cada capa se nombra con un prefijo:
    · `slot:image`      → Slot imagen (cover de fondo)
    · `slot:title`      → Slot de título
    · `slot:subtitle`   → Slot de subtítulo
    · `slot:pillar_tag` → Slot del pilar (small caps)
    · `slot:logo`       → Slot para el logo
    · `deco:rect`       → Rectángulo de decoración (fill + opacity)
    · `deco:hairline`   → Línea fina
    · `deco:gradient_v` → Gradiente vertical (usa primer color del fill)
    · `deco:corner_brackets` → Corchetes de esquina

Propiedades opcionales para TEXT (como node description):
  font=body_semibold size=22 color=#E59500 upper=true track=0.28 maxLines=1 align=left

Uso:
    uv run python -m bot_estiv.tools.figma_sync

Cachea en packages/brand/templates/<name>.json. El renderer las prefiere
sobre las BUILTIN al encontrarlas ahí.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def _templates_dir() -> Path:
    env_path = os.getenv("BRAND_TEMPLATES_DIR")
    candidates = [Path(env_path)] if env_path else []
    here = Path(__file__).resolve()
    candidates.append(Path("/app/packages/brand/templates"))
    candidates.extend(parent / "packages" / "brand" / "templates" for parent in here.parents)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else Path("packages/brand/templates")


_TEMPLATES_DIR = _templates_dir()
_FIGMA_API = "https://api.figma.com/v1"


# ========== Helpers ==========


def _color_to_hex(c: dict | None) -> str:
    if not c:
        return "#000000"
    r = int(round(c.get("r", 0) * 255))
    g = int(round(c.get("g", 0) * 255))
    b = int(round(c.get("b", 0) * 255))
    return f"#{r:02X}{g:02X}{b:02X}"


def _node_opacity(node: dict) -> float:
    # Prioridad: opacity explícito del nodo > alpha del primer fill
    if node.get("opacity") is not None:
        return float(node["opacity"])
    fills = node.get("fills") or []
    if fills:
        first = fills[0]
        c = first.get("color") or {}
        return float(c.get("a", 1.0)) * float(first.get("opacity", 1.0))
    return 1.0


def _first_solid_fill(node: dict) -> tuple[str, float]:
    for fill in node.get("fills") or []:
        if fill.get("visible") is False:
            continue
        if fill.get("type") == "SOLID":
            hex_color = _color_to_hex(fill.get("color") or {})
            opacity = _node_opacity(node)
            return hex_color, opacity
    return "#000000", _node_opacity(node)


def _abs_bbox(node: dict, frame_origin: tuple[float, float]) -> tuple[int, int, int, int]:
    box = node.get("absoluteBoundingBox") or {}
    fx, fy = frame_origin
    x1 = int(round(box.get("x", 0) - fx))
    y1 = int(round(box.get("y", 0) - fy))
    w = int(round(box.get("width", 0)))
    h = int(round(box.get("height", 0)))
    return (x1, y1, x1 + w, y1 + h)


def _parse_text_props(description: str) -> dict:
    """Parsea 'font=body_semibold size=22 track=0.28 upper=true' → dict."""
    props: dict[str, object] = {}
    if not description:
        return props
    for token in re.findall(r"(\w+)=([^\s]+)", description):
        k, v = token
        # bools
        if v.lower() in ("true", "false"):
            props[k] = v.lower() == "true"
        else:
            # números
            try:
                if "." in v:
                    props[k] = float(v)
                else:
                    props[k] = int(v)
            except ValueError:
                props[k] = v
    return props


def _walk(node: dict):
    yield node
    for ch in node.get("children") or []:
        yield from _walk(ch)


# ========== Conversión ==========


def _build_spec(frame: dict, template_name: str) -> dict:
    """Convierte un frame de Figma a spec dict."""
    frame_box = frame.get("absoluteBoundingBox") or {}
    fx, fy = frame_box.get("x", 0), frame_box.get("y", 0)
    W = int(round(frame_box.get("width", 1080)))
    H = int(round(frame_box.get("height", 1350)))

    slots: dict[str, dict] = {}
    decorations: list[dict] = []

    for node in _walk(frame):
        if node is frame:
            continue
        name = node.get("name") or ""
        desc = node.get("description") or ""

        if name.startswith("slot:"):
            slot_name = name.split(":", 1)[1].strip()
            bbox = _abs_bbox(node, (fx, fy))
            text_props = _parse_text_props(desc)

            if slot_name == "image":
                slots["image"] = {"bbox": list(bbox), "fit": text_props.get("fit", "cover")}
            elif slot_name == "logo":
                slots["logo"] = {"bbox": list(bbox)}
            else:  # text slot
                # si es TEXT node, leer color y tamaño desde el nodo
                style = node.get("style") or {}
                fill_hex = "#FFFFFF"
                for fill in node.get("fills") or []:
                    if fill.get("type") == "SOLID":
                        fill_hex = _color_to_hex(fill.get("color") or {})
                        break
                slots[slot_name] = {
                    "bbox": list(bbox),
                    "font_kind": str(text_props.get("font", "body")),
                    "font_size_px": int(text_props.get("size", style.get("fontSize", 24))),
                    "color": str(text_props.get("color", fill_hex)),
                    "align": str(text_props.get("align", "left")),
                    "uppercase": bool(text_props.get("upper", False)),
                    "tracking_em": float(text_props.get("track", 0.0)),
                    "line_spacing": float(text_props.get("line", 1.2)),
                    "max_lines": int(text_props.get("maxLines", 3)),
                }

        elif name.startswith("deco:"):
            deco_type = name.split(":", 1)[1].strip()
            bbox = _abs_bbox(node, (fx, fy))
            fill, opacity = _first_solid_fill(node)
            text_props = _parse_text_props(desc)
            decorations.append(
                {
                    "type": deco_type,
                    "bbox": list(bbox),
                    "fill": fill,
                    "opacity": round(opacity, 3),
                    "weight": int(text_props.get("weight", 2)),
                    "corner_len": int(text_props.get("corner", 60)),
                    "direction": str(text_props.get("dir", "bottom-up")),
                }
            )

    return {
        "name": template_name,
        "size": [W, H],
        "slots": slots,
        "decorations": decorations,
    }


# ========== Fetch ==========


def fetch_file(file_key: str, token: str) -> dict:
    headers = {"X-Figma-Token": token}
    url = f"{_FIGMA_API}/files/{file_key}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


def _iter_template_frames(doc: dict):
    """Itera sobre los frames de primer nivel que se llaman `template:*`."""
    for node in _walk(doc):
        if node.get("type") in ("FRAME", "COMPONENT") and (node.get("name") or "").startswith(
            "template:"
        ):
            yield node


def sync(
    file_key: str | None = None,
    token: str | None = None,
    out_dir: Path | None = None,
) -> list[Path]:
    """Ejecuta el sync y devuelve la lista de specs escritas."""
    file_key = file_key or settings.figma_templates_file_key
    token = token or settings.figma_access_token
    out_dir = out_dir or _TEMPLATES_DIR

    if not file_key or not token:
        raise RuntimeError(
            "Faltan FIGMA_ACCESS_TOKEN o FIGMA_TEMPLATES_FILE_KEY en .env"
        )

    logger.info("figma.sync.start", extra={"file_key": file_key})
    data = fetch_file(file_key, token)
    root = data.get("document", {})
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for frame in _iter_template_frames(root):
        template_name = frame["name"].split(":", 1)[1].strip()
        if not template_name:
            continue
        spec = _build_spec(frame, template_name)
        out = out_dir / f"{template_name}.json"
        out.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("figma.sync.wrote", extra={"name": template_name, "path": str(out)})
        written.append(out)

    logger.info("figma.sync.done", extra={"count": len(written)})
    return written


# ========== CLI ==========

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-key", dest="file_key", default=None)
    parser.add_argument("--token", dest="token", default=None)
    parser.add_argument("--out", dest="out", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    out = Path(args.out) if args.out else None
    try:
        paths = sync(args.file_key, args.token, out)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Sincronizadas {len(paths)} plantillas desde Figma.")
    for p in paths:
        print(f"  - {p}")
