# Bot Estiv — Multiagente de Marketing Digital

Sistema multi-agente para **Gardens Wood** accesible vía WhatsApp. Orquestado con
LangGraph + FastAPI, con dashboard Next.js.

## Estructura

```
bot-estiv/
├── apps/
│   ├── api/           # FastAPI + LangGraph (Python 3.12)
│   ├── worker/        # ARQ worker para jobs async + cron
│   └── dashboard/     # Next.js 15 + shadcn/ui
├── packages/
│   ├── brand/         # Tokens de marca (paleta, fonts, logo rules)
│   └── shared-types/  # Tipos compartidos
└── infra/
    ├── docker-compose.yml
    └── init-db.sql
```

## Inicio rápido

1. Copiá `.env.example` a `.env` y rellená credenciales.
2. Levantá la infra:

```bash
cd infra
docker compose up -d postgres redis
```

3. API + worker:

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn bot_estiv.main:app --reload
```

```bash
cd apps/worker
uv sync
uv run arq bot_estiv.schedulers.worker.WorkerSettings
```

4. Dashboard:

```bash
cd apps/dashboard
pnpm install
pnpm dev
```

## Flujos principales

- **Webhook WhatsApp** (`POST /webhook/twilio`) → Director LangGraph → agentes → cola de aprobación
- **Cron semanal** (Lun 09:00) → CampaignPlanner → recordatorio por WhatsApp
- **Publicación programada** → ARQ job → Meta Graph API (IG/FB)

Ver fases completas en [../Branding/Manual de Identidad de Marca_ Gardens Wood.txt](../Branding/Manual%20de%20Identidad%20de%20Marca_%20Gardens%20Wood.txt).
