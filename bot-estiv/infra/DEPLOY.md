# Deploy de Bot Estiv

Tres componentes a desplegar: **API** (FastAPI), **worker** (ARQ) y **dashboard** (Next.js).
La base de datos Postgres + pgvector y Redis pueden ser managed (Neon / Supabase / Upstash).

## Windows: Docker local + migraciones

1. Instalar **Docker Desktop** y dejarlo en ejecución (icono de ballena en la barra; el `docker` debe existir en el PATH).
2. Tener **uv** en el PATH: [documentación de uv](https://docs.astral.sh/uv/getting-started/installation/) o `irm https://astral.sh/uv/install.ps1 | iex`.
3. En la carpeta `bot-estiv` interna (la que tiene `apps/`, `infra/`, `.env`):

```powershell
.\scripts\levantar-docker-y-migrar.ps1
```

Eso levanta `postgres` y `redis` con `docker compose` y ejecuta `alembic upgrade head`. Luego levantá la API, el worker y el dashboard según [ONBOARDING.md](../../ONBOARDING.md).

## VPS Hostinger (Docker Compose + Nginx + SSL)

Esta opción deja todo en un único VPS: **API**, **worker**, **dashboard**, **Postgres con pgvector** y **Redis**. Está pensada para Ubuntu LTS en Hostinger.

### 1. DNS

Definir los subdominios y apuntarlos con registros `A` a la IP pública del VPS:

- `bot-estiv.gardenswood.com.ar` → dashboard
- `api.bot-estiv.gardenswood.com.ar` → API y webhook de Twilio

Si se usa otro dominio, cambiar los valores en `.env` y en la plantilla de Nginx.

### 2. Preparar el servidor

Conectarse por SSH al VPS y ejecutar el setup base:

```bash
sudo bash scripts/setup-hostinger-vps.sh
```

El script instala Docker, Docker Compose, Nginx, Certbot, Git, `ufw`, carpetas persistentes bajo `/opt/bot-estiv` y rotación básica de logs Docker.

Importante si el VPS ya corre otro bot: por defecto **no activa** `ufw`, para no bloquear puertos existentes. Si ya conocés todos los puertos necesarios, podés activarlo así:

```bash
sudo BOT_ESTIV_ENABLE_UFW=1 BOT_ESTIV_EXTRA_UFW_PORTS="8080 9000" bash scripts/setup-hostinger-vps.sh
```

Reemplazá `8080 9000` por los puertos reales del otro bot, o dejalo vacío si ese bot también entra solo por `80/443`.

### 3. Clonar repo y configurar secretos

```bash
cd /opt/bot-estiv/app
git clone https://github.com/vjlale/bot-estiv.git
cd bot-estiv/bot-estiv
cp .env.vps.example .env
nano .env
```

Completar como mínimo:

- `POSTGRES_PASSWORD`, `DATABASE_URL`, `DATABASE_URL_SYNC`
- `BOT_ESTIV_DASHBOARD_DOMAIN`, `BOT_ESTIV_API_DOMAIN`, `NEXT_PUBLIC_API_BASE_URL`
- `BOT_ESTIV_LETSENCRYPT_EMAIL`
- `GOOGLE_API_KEY`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `TWILIO_WHATSAPP_TO`
- Credenciales `META_*`, `S3_*`, `FIGMA_*` y `SENTRY_DSN` si aplican.

En producción, las URLs internas deben usar los nombres de servicio Docker:

```env
DATABASE_URL=postgresql+asyncpg://postgres:<password>@postgres:5432/bot_estiv
DATABASE_URL_SYNC=postgresql://postgres:<password>@postgres:5432/bot_estiv
REDIS_URL=redis://redis:6379/0
BRAND_LOGO_PATH=/branding/LOGOCOMPLETO.png
BRAND_MANUAL_PATH=/branding/Manual de Identidad de Marca_ Gardens Wood.txt
NEXT_PUBLIC_API_BASE_URL=https://api.bot-estiv.gardenswood.com.ar
```

Copiar los assets de marca al servidor:

```bash
sudo mkdir -p /opt/bot-estiv/branding
sudo cp -r /ruta/al/Branding/* /opt/bot-estiv/branding/
```

### 4. Deploy, migraciones y SSL

Desde `bot-estiv/bot-estiv` en el VPS:

```bash
chmod +x scripts/*hostinger-vps.sh
./scripts/deploy-hostinger-vps.sh
```

El deploy:

1. Construye imágenes.
2. Levanta Postgres y Redis.
3. Ejecuta `alembic upgrade head`.
4. Levanta API, worker y dashboard.
5. Emite certificados con Certbot.
6. Instala Nginx HTTPS desde `infra/nginx/bot-estiv.conf`.

Para una prueba sin SSL, usar `SKIP_TLS=1 ./scripts/deploy-hostinger-vps.sh`, pero Twilio en producción debe usar HTTPS.

### 5. Verificación

```bash
./scripts/status-hostinger-vps.sh
docker compose --env-file .env -f infra/docker-compose.vps.yml logs -f api
docker compose --env-file .env -f infra/docker-compose.vps.yml logs -f worker
```

Verificar:

- `https://api.bot-estiv.gardenswood.com.ar/health`
- `https://bot-estiv.gardenswood.com.ar`
- Dashboard → **Configuración**, donde se ve entorno, dominios, webhook esperado y presencia de variables críticas sin revelar secretos.
- Twilio Console → webhook `https://api.bot-estiv.gardenswood.com.ar/webhook/twilio`.
- Prueba real WhatsApp: mensaje entrante, respuesta, worker sin errores y datos visibles en dashboard.

### 6. Backups y restore

Backup manual:

```bash
./scripts/backup-hostinger-vps.sh
```

Restore:

```bash
./scripts/restore-hostinger-vps.sh /opt/bot-estiv/backups/bot-estiv-postgres-YYYYMMDD-HHMMSS.dump /opt/bot-estiv/backups/bot-estiv-media-YYYYMMDD-HHMMSS.tar.gz
```

Recomendado: programar `backup-hostinger-vps.sh` con cron diario y copiar `/opt/bot-estiv/backups` fuera del VPS.

## Despliegue a Railway (CLI en Windows)

No hace falta instalar un binario global: se usa `npx`.

```powershell
cd <ruta>\bot-estiv
npx @railway/cli login
npx @railway/cli link
```

Configurar en el panel de Railway las variables de entorno (mismo esquema que `.env.example`) y los plugins **Postgres** y **Redis** si no usás URLs externas.

**Token para CI o sin navegador:** en Railway → Account → Tokens, generar un token y en PowerShell:

```powershell
$env:RAILWAY_TOKEN = "tu_token"
npx @railway/cli up -s api
npx @railway/cli up -s worker
npx @railway/cli up -s dashboard
```

(Los nombres `api` / `worker` / `dashboard` deben coincidir con los servicios creados en el proyecto.)

Atajo en el repo: `.\scripts\desplegar-railway.ps1 -Service api` (y análogo para `worker` y `dashboard`).

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
| --- | --- | --- |
| API + worker | Railway / Fly.io | 20–40 |
| Postgres (+pgvector) | Neon / Supabase | 0–25 |
| Redis | Upstash free tier | 0 |
| Storage media | Cloudflare R2 | 1–5 |
| Twilio WhatsApp | pay per message | 20–80 |
| OpenAI + Gemini | APIs | 50–200 |
| **Total** | | **~100–350 USD/mes** |
