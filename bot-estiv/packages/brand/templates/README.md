# Plantillas de overlay — cache local

Esta carpeta contiene los specs JSON sincronizados desde Figma. Cada archivo
se llama como el `template:<name>` del Figma y es consumido por
`bot_estiv.tools.template_renderer.load_template`.

## Regenerar

```bash
# desde la raíz del repo
make fetch-templates
```

Esto corre `python -m bot_estiv.tools.figma_sync` y tira los JSON acá.

## Formato

```json
{
  "name": "editorial_hero",
  "size": [1080, 1350],
  "slots": {
    "image": {"bbox": [0, 0, 1080, 1350], "fit": "cover"},
    "title": {"bbox": [...], "font_kind": "heading_bold", "font_size_px": 68, ...},
    ...
  },
  "decorations": [
    {"type": "gradient_v", "bbox": [...], "fill": "#36454F", "opacity": 0.92, "direction": "bottom-up"},
    ...
  ]
}
```

Si no existe un JSON para una plantilla, el renderer usa la versión
BUILTIN hardcodeada en [template_renderer.py](../../../apps/api/src/bot_estiv/tools/template_renderer.py).
