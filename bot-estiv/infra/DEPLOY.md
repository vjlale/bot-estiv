# Deploy de Bot Estiv

Tres componentes a desplegar: **API** (FastAPI), **worker** (ARQ) y **dashboard** (Next.js).
La base de datos Postgres + pgvector y Redis pueden ser managed (Neon / Supabase / Upstash).

## Opción A — Railway (más simple)

1. `railway login && railway init` en la raíz del repo
2. Crear 3 services: `api`, `worker`, `dashboard`
3. Configurar Postgres + Redis como plugins Railway
4. Variables de entorno: copiar `.env.example` y rellenar en cada service
5. Deploy:

```bash
railway up --service api
railway up --service worker
railway up --service dashboard
```

## Opción B — Fly.io

```bash
# API
fly launch --copy-config --config infra/fly.api.toml --dockerfile apps/api/Dockerfile
fly secrets set DATABASE_URL=... REDIS_URL=... OPENAI_API_KEY=... TWILIO_ACCOUNT_SID=... ...
fly deploy --config infra/fly.api.toml

# Worker
fly launch --copy-config --config infra/fly.worker.toml --dockerfile apps/api/Dockerfile
fly secrets set $(cat .env | xargs)
fly deploy --config infra/fly.worker.toml
```

Postgres: `fly postgres create` + instalar extensión pgvector:

```bash
fly postgres connect -a <db-app>
=> CREATE EXTENSION vector;
```

Redis: `fly redis create` o usar Upstash.

## Opción C — Cloud Run + Cloud SQL + Memorystore

- Build y push a Artifact Registry.
- Cloud Run service `bot-estiv-api` con min instances = 1 (webhook Twilio no tolera cold starts >15s).
- Cloud Run Job `bot-estiv-worker` disparado por Cloud Scheduler.
- Cloud SQL Postgres con extensión pgvector (disponible en PG 15+).
- Memorystore Redis.

## Post-deploy: verificación WhatsApp con Meta

El sandbox Twilio WhatsApp sirve para pruebas. Para producción:

1. **Meta Business Manager** → crear/verificar negocio Gardens Wood.
2. **Twilio Console** → Messaging → WhatsApp senders → solicitar número.
3. **Display Name approval**: "Gardens Wood" (puede tardar 1–3 días).
4. **Webhook URL**: apuntar a `https://<tu-api>/webhook/twilio` y guardar.
5. **Signature validation**: en `APP_ENV=production` la ruta exige `X-Twilio-Signature`.
6. **Plantillas (Content Templates)**: para iniciar conversaciones fuera de la
   ventana de 24h, crear un Content Template con placeholders y aprobarlo en Meta.

## Monitoreo

- **Sentry**: set `SENTRY_DSN` y listo. FastAPI + ARQ auto-reportan errores.
- **Logs estructurados**: stdout → agregador de Railway/Fly (o configurar Logflare).
- **Métricas**: exponer `/metrics` Prometheus (ver TODO opcional), scrape con Grafana Cloud.

## DNS y dominio

- `bot-estiv.gardenswood.com.ar` → dashboard
- `api.bot-estiv.gardenswood.com.ar` → API
- `media.gardenswood.com.ar` → CNAME al bucket R2

## Costos estimados (AR, orden de magnitud mensual)

| Componente | Servicio | USD/mes aprox |
|---|---|---|
| API + worker | Railway / Fly.io | 20–40 |
| Postgres (+pgvector) | Neon / Supabase | 0–25 |
| Redis | Upstash free tier | 0 |
| Storage media | Cloudflare R2 | 1–5 |
| Twilio WhatsApp | pay per message | 20–80 |
| OpenAI + Gemini | APIs | 50–200 |
| **Total** | | **~100–350 USD/mes** |
