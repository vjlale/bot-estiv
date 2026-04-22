---
name: real-photo-curator
description: Filosofía y guía técnica para procesar FOTOS REALES de obras de Gardens Wood. Úsala cuando necesites ajustar el LUT de color grading, los criterios de selección de portada, los roles narrativos o la heurística del RealPhotoCurator. La foto real siempre manda; la AI no altera contenido.
---

# RealPhotoCurator — procesar fotos reales de obras

## Filosofía

> **La foto real es sagrada**. La obra que el cliente construyó, lo que le llevó semanas, el detalle que cuidó — eso no se toca con AI. La fidelidad al trabajo real es parte de la identidad de Gardens Wood.

Este skill aplica a fotos recibidas de:
- **WhatsApp**: cliente manda 8-12 fotos con `#proyecto-nombre` → `webhook._handle` las descarga y crea `SourceAsset`.
- **Dashboard**: upload directo en `/library`.

**NO se usa Nano Banana ni ninguna IA generativa** sobre fotos reales. Solo:
1. **Color grading** con LUT determinista (curvas RGB hardcodeadas).
2. **Auto-crop** al formato destino centrado en el centro de masa de la energía de imagen.
3. **Selección de portada** por heurística sharpness + regla de tercios + aspect match.
4. **Overlay** de plantilla del TemplateRenderer (tipografía + decoraciones de marca).

## Stack técnico

| Módulo | Responsabilidad |
|---|---|
| `apps/api/src/bot_estiv/tools/photo_editor.py` | LUT color grading, auto crop, pick_cover |
| `apps/api/src/bot_estiv/agents/real_photo_curator.py` | Asignación de roles narrativos y plantillas |
| `apps/api/src/bot_estiv/agents/content_designer.py::generate_post_from_photos` | Pipeline completo de fotos reales |

## Color grading Gardens Wood — "Warm Quebracho"

Ubicación: `photo_editor._apply_rgb_curves`.

### Intención

- **Shadows más cálidas** (+rojo, -azul) → madera + piel argentinos en golden hour.
- **Mids levemente desaturados en verdes** → pastos no "chillones" tipo cancha de fútbol.
- **Highlights protegidos** → no reventar el cielo de la hora dorada.

### Curvas actuales

```python
# R: shadows calientes, highlights intactos
if v < 64:  v * 1.18
elif v < 160: v * 1.06
else: v * 1.02

# G: desaturar verdes sutilmente
v * 0.97

# B: menos azul en sombras
if v < 80: v * 0.85
elif v < 180: v * 0.95
else: v
```

### Ajustes globales post-curvas

- `contrast * 1.08` — medios con más cuerpo
- `saturation * 0.95` — bajar el ruido de color 5%
- `brightness * 1.02` — un toque de aire

### Cuándo intervenir

- Fotos muy oscuras (interiores/mañanas grises): considerar aumentar `strength` o exponer antes.
- Fotos con mucho verde (pastos, eucaliptos): el LUT lo contiene, no bajar `saturation` más.
- Fotos con cielos azules: el LUT no lo protege perfecto; si vemos cielos virados a morado, subir `curve_b` en highlights a `>= 1.0`.

## Roles narrativos del carrusel

El `RealPhotoCurator.curate` asigna cada foto a un rol según su "carácter visual":

| Posición | Rol | Heurística | Plantilla |
|---|---|---|---|
| 1 | **apertura** | pick_cover (sharpness + tercios + aspect) | `cover_hero` |
| 2 | **detalle** | mayor sharpness del resto | `minimal_stamp` |
| 3 | **lifestyle** | mejor rule_of_thirds del resto | `editorial_hero` |
| 4 | **cierre** | mayor openness (baja varianza L) | `split_60_40` |
| 5 | **spec** | residual | `spec_card` |

Si el cliente manda < 4 fotos, se asignan los primeros N roles.

### Heurísticas en detalle

- **sharpness**: varianza del Laplaciano aproximado. Foto más enfocada = mejor. Fotos de detalle tienden a ganar por textura.
- **rule_of_thirds**: distancia del centro de masa (energía) a la intersección de tercios más cercana. Normalizado 0-1.
- **openness**: inverso de la varianza en canal L. Una foto de un paisaje abierto tiene baja varianza.

## Criterios para elegir portada

La portada del carrusel es la cara del post. Se elige con un score ponderado:

```
score = 0.45 * sharpness + 0.30 * rule_of_thirds + 0.25 * aspect_match
```

Donde `aspect_match` es cuán cerca está el ratio de la foto al ratio destino (1080×1350 = 0.8 para IG portrait).

### Tips editoriales

- **No elegir fotos con rostros reconocibles** como portada a menos que el cliente lo pidió. Gardens Wood comunica espacios, no personas.
- **Preferir golden hour / luz oblicua** sobre mediodía plano.
- **Portadas verticales** > cuadradas > horizontales.

## Qué NO hacer

- No usar Nano Banana para "mejorar" una foto real → rompe la filosofía.
- No aplicar filtros de Instagram/Lightroom encima del LUT — el LUT ya los reemplaza.
- No clonar objetos ni remover elementos: si un cable eléctrico arruina la foto, **no la elegimos**, no la editamos.
- No inventar datos en `spec_card` (metros, garantía) que no vengan del cliente.

## Workflow del usuario (recordatorio)

1. Cliente manda 8-12 fotos de la obra por WhatsApp con caption `#cerco-mendiolaza obra terminada`.
2. `webhook._handle` detecta `num_media > 0`, descarga + guarda como `SourceAsset(project_tag="cerco-mendiolaza", channel="whatsapp")`.
3. Bot responde por WA: *"Recibí 12 fotos para #cerco-mendiolaza. Decime *generá carrusel cerco-mendiolaza* cuando quieras armar la pieza."*
4. Cuando el cliente lo dice, el Director invoca a RealPhotoCurator + ContentDesigner.generate_post_from_photos → 4 slides renderizadas con plantillas.
5. Copywriter arma title/caption/hashtags desde el `project_tag` + contexto del manual.
6. BrandGuardian valida contrast + legibilidad + logo.
7. Preview al cliente con botones APROBAR / EDITAR / CANCELAR.

## Extender

Para agregar un nuevo rol narrativo:
1. Agregar key a `NARRATIVE_ROLES` en `real_photo_curator.py`.
2. Mapear plantilla en `TEMPLATE_BY_ROLE`.
3. Extender la función `curate` con la heurística.
4. Agregar plantilla al sistema (ver skill `post-templates`).
