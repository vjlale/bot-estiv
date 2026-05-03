---
name: canva-migration
description: Guía para migrar el motor de plantillas de Bot Estiv de Pillow (hoy) a Canva Connect API (Autofill) cuando haya upgrade a Canva Enterprise. Incluye mapping de las 7 plantillas BUILTIN a Brand Templates de Canva, OAuth setup, stub de `tools/canva_sync.py` y checklist de cuándo ejecutar la migración. Usar cuando el user diga que ya tiene Canva Enterprise o esté planificando upgradear.
---

# Migración a Canva Connect API

## Contexto

Hoy Bot Estiv renderiza las 7 plantillas en código con Pillow (ver `apps/api/src/bot_estiv/tools/template_renderer.py`). Funciona, es rápido, pero los layouts viven en Python y cualquier cambio requiere dev.

Cuando Gardens Wood (o ALENIA gestionando múltiples clientes) pase a Canva Enterprise, pasamos a usar **Canva Connect Autofill API**: los diseños viven en Canva y el bot los llama por API con datos. Beneficios:
- La marca o vos pueden ajustar layouts visualmente sin tocar código
- Cada variación es una "Brand Template" Canva
- Calidad gráfica al nivel del equipo de diseño que la armó

## Requisitos previos

1. **Canva Enterprise activo** (sin esto la Autofill API devuelve 403).
2. **Cuenta en https://www.canva.com/developers** con un "Integration" creado.
3. **Permisos/Scopes del Integration**:
   - `brandtemplate:meta:read`
   - `brandtemplate:content:read`
   - `design:content:read`
   - `design:content:write`
   - `asset:read`, `asset:write`
4. **Redirect URI** configurada (para el OAuth flow): `https://<TU-DOMINIO>/oauth/canva/callback`.

Opción desarrollo (sin Enterprise todavía): solicitar development access en el Developer Portal explicando el caso de uso. Aprobación en 3-5 días hábiles. **Limitación**: aunque te aprueben el desarrollo, cuando un usuario real use la integración debe ser Enterprise.

## Mapping plantillas actuales → Brand Templates Canva

Cada BUILTIN de `template_renderer.py` se convierte en una Brand Template Canva. Naming convention sugerida:

| Pillow template | Canva Brand Template | Data fields (autofillable) |
|---|---|---|
| `editorial_hero` | `GW — Editorial Hero` | `title` (text), `subtitle` (text), `pillar_tag` (text), `image_hero` (image) |
| `minimal_stamp` | `GW — Minimal Stamp` | `pillar_tag` (text), `image_hero` (image) |
| `cover_hero` | `GW — Cover Hero` | `title` (text), `subtitle` (text), `image_hero` (image) |
| `split_60_40` | `GW — Split 60/40` | `title`, `subtitle`, `pillar_tag`, `image_hero` |
| `spec_card` | `GW — Spec Card` | `title`, `subtitle`, `pillar_tag`, `image_hero` |
| `infographic_dimensions` | `GW — Dimensions` | `title`, `dim_top_label`, `dim_right_label`, `description_title`, `description_body`, `image_hero` |
| `numbered_steps` | `GW — Numbered Steps` | `title`, `step_1_title`, `step_1_body`, `step_2_title`, `step_2_body`, `step_3_title`, `step_3_body`, `image_hero` |

**Convención de data fields en Canva**: usar los mismos nombres que los slots de `template_renderer`. Así el mapping código → Canva es 1:1 y no hay que traducir nombres.

Para agregar data fields autofillable en Canva: abrir el design → menú **Apps → Data autofill** → marcar cada layer como autofillable con el nombre del slot.

## Env vars que se agregan

```bash
# .env
CANVA_CLIENT_ID=
CANVA_CLIENT_SECRET=
CANVA_REDIRECT_URI=https://tu-dominio.com/oauth/canva/callback
# Map nombre_template → brand_template_id de Canva (JSON string)
CANVA_TEMPLATE_IDS='{"editorial_hero":"AEN...","numbered_steps":"AEN..."}'
```

## Stub: `apps/api/src/bot_estiv/tools/canva_sync.py`

Este archivo se crea cuando se migra. Esqueleto sugerido:

```python
"""Canva Connect API: autofill Brand Templates y export como PNG.

Flujo de una pieza:
    1. fetch_template_dataset(id) — para saber qué fields acepta (debug only)
    2. create_autofill_job(id, {field: value, ...}) → job_id
    3. poll_autofill_job(job_id) hasta status='success' → design_id
    4. export_design_png(design_id) → bytes

Reemplaza a template_renderer.render() como motor primario. Fallback:
si la pieza falla (403, timeout, quota), caer a Pillow BUILTIN.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import httpx

from ..config import settings

CANVA_API = "https://api.canva.com/rest/v1"


async def create_autofill_job(
    token: str,
    brand_template_id: str,
    data_fields: dict[str, Any],
    title: str | None = None,
) -> str:
    # Convierte `{"title": "Hola"}` al payload de Canva
    payload = {
        "brand_template_id": brand_template_id,
        "data": {
            k: ({"type": "text", "text": v} if isinstance(v, str)
                else {"type": "image", "asset_id": v["asset_id"]})
            for k, v in data_fields.items()
        },
    }
    if title:
        payload["title"] = title

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{CANVA_API}/autofills",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["job"]["id"]


async def poll_autofill_job(
    token: str, job_id: str, max_wait_s: int = 60
) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        deadline = time.time() + max_wait_s
        while time.time() < deadline:
            resp = await client.get(
                f"{CANVA_API}/autofills/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()["job"]
            if data["status"] == "success":
                return data["result"]["design"]
            if data["status"] == "failed":
                raise RuntimeError(f"Canva autofill failed: {data}")
            await asyncio.sleep(2.0)
        raise TimeoutError(f"Canva autofill job {job_id} took >{max_wait_s}s")


async def export_design_png(token: str, design_id: str) -> bytes:
    # POST /v1/exports con format=png → polling → URL → GET bytes
    async with httpx.AsyncClient(timeout=60) as client:
        job = await client.post(
            f"{CANVA_API}/exports",
            headers={"Authorization": f"Bearer {token}"},
            json={"design_id": design_id, "format": {"type": "png"}},
        )
        job.raise_for_status()
        job_id = job.json()["job"]["id"]

        # polling hasta status=success
        for _ in range(30):
            r = await client.get(
                f"{CANVA_API}/exports/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            data = r.json()["job"]
            if data["status"] == "success":
                url = data["urls"][0]
                dl = await client.get(url)
                dl.raise_for_status()
                return dl.content
            if data["status"] == "failed":
                raise RuntimeError(f"Canva export failed: {data}")
            await asyncio.sleep(2.0)
        raise TimeoutError("Canva export timeout")


async def render_via_canva(
    template_name: str,
    values: dict[str, Any],
    title: str | None = None,
) -> bytes:
    """Drop-in replacement para template_renderer.render() usando Canva."""
    token = _get_user_oauth_token()  # de la sesión del usuario
    ids = json.loads(os.environ["CANVA_TEMPLATE_IDS"])
    brand_template_id = ids[template_name]
    job_id = await create_autofill_job(
        token, brand_template_id, values, title=title
    )
    design = await poll_autofill_job(token, job_id)
    return await export_design_png(token, design["id"])
```

## OAuth flow (alto nivel)

Canva Connect usa **Authorization Code + PKCE**. En el bot:

1. User click "Conectar Canva" en el dashboard → redirect a `https://www.canva.com/api/oauth/authorize?client_id=...&redirect_uri=...&scope=...&code_challenge=...`
2. User acepta → Canva redirige a `CANVA_REDIRECT_URI` con `?code=...`
3. Backend hace `POST /oauth/token` con code + code_verifier → recibe `access_token` + `refresh_token`
4. Tokens se persisten en DB (nueva tabla `user_oauth_tokens(user_id, provider, access_token, refresh_token, expires_at)`)
5. Cuando el bot renderiza una pieza, toma el token del user y lo usa en `Authorization: Bearer`.
6. Refresh automático antes de expire.

## Migration checklist (cuándo ejecutar)

Migrar a Canva Autofill tiene sentido cuando:
- **Volumen**: ≥50 posts/mes generados (antes no compensa el costo Enterprise).
- **Multi-cliente**: ALENIA gestiona 3+ marcas y cada una quiere su propio look editable.
- **Ownership visual**: la marca quiere iterar plantillas sin pasar por dev.

Hasta que se cumpla, seguimos con Pillow + BUILTIN (ya profesional, funcionando).

## Plan de migración (2-4 horas de dev)

1. Crear las 7 Brand Templates en Canva replicando layouts actuales (trabajo del diseñador, ~4-8 h).
2. Agregar data fields autofillable con los nombres del mapping.
3. Copiar los Brand Template IDs al `.env`.
4. Implementar `tools/canva_sync.py` según el stub.
5. Agregar tabla `user_oauth_tokens` (migración Alembic `0003_user_oauth.py`).
6. Implementar el OAuth callback en `apps/api/src/bot_estiv/routers/oauth.py`.
7. En `content_designer`, agregar flag `use_canva=True` (leer de settings) y condicional `if settings.canva_enabled: render_via_canva(...) else: template_renderer.render(...)`.
8. Fallback robusto: si Canva falla (timeout, quota, etc.), `try/except` cae a Pillow. Log + alerta.
9. Tests: mockear httpx + validar payload correcto a la API.
10. Rollout: primero solo `editorial_hero` via Canva, monitorear 1 semana, después migrar el resto.

## Costos a tener en cuenta

- **Canva Enterprise**: USD 30+/user/mes (contacto comercial, muy variable).
- **Rate limits Autofill**: 100 jobs/min por integration (más que suficiente para Gardens Wood).
- **Latencia**: async job puede tardar 5-15 s por pieza. No impacta si rendereamos proactivamente en background (ARQ jobs) en vez de por demanda.

## Fallback siempre-on

Incluso con Canva activo, mantener `template_renderer` BUILTIN como fallback:
- Red de seguridad si la API falla (SLA Canva no es 100%).
- Permite desarrollo local sin tokens.
- Permite rollback rápido si un cambio en Canva rompe layout.

El flag `settings.canva_enabled` controla el primary engine; el fallback siempre está disponible.
