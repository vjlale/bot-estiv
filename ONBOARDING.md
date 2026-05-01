# Bot-Estiv — Guía rápida (para la PC del trabajo)

Este repo contiene:

- `bot-estiv/`: API + worker (Python/FastAPI/LangGraph) y dashboard (Next.js)
- `Branding/`: assets y manual de marca (usado por la API/infra)

---

## 0) Requisitos en la PC

| Herramienta | Uso |
| ----------- | --- |
| **Node.js 20+** (con `npm`) | Dashboard Next.js |
| **Python 3.12+** y **`uv`** | API, worker, migraciones (`uv sync`, `alembic`, `arq`) |
| **Docker Desktop** (o motor compatible) | Postgres + Redis (`infra/docker-compose.yml`) |

Si `python` o `uv` no están en el PATH, instalá `uv` con: `python -m pip install -U uv` (después de tener Python).

---

## 1) Clonar el repo (PC del trabajo)

Abrí PowerShell en la carpeta donde querés el proyecto y corré:

```powershell
git clone https://github.com/vjlale/bot-estiv.git
cd bot-estiv
```

---

## 2) Variables de entorno (.env) — obligatorio

El repo **NO** incluye secretos. En `bot-estiv\` ya podés tener un `.env` generado desde la plantilla; si no existe, crealo así:

```powershell
cd .\bot-estiv
Copy-Item -Path .\.env.example -Destination .\.env -Force
notepad .\.env
```

- Completá al menos: **`GOOGLE_API_KEY`**, **Twilio** (`TWILIO_*`) y, según lo que uses, **Meta**, **S3/R2**, **Figma**.
- **No subas** `.env` (está ignorado por Git).

**Dashboard (Next.js):** la API se apunta con `NEXT_PUBLIC_API_BASE_URL` (por defecto `http://localhost:8000`). Ese valor vive en `bot-estiv\apps\dashboard\.env.local` (ya puede existir; si no, copiá `apps\dashboard\.env.local.example` a `apps\dashboard\.env.local`).

---

## 3) Infra con Docker (Postgres + Redis)

Desde la raíz del repo:

```powershell
cd .\bot-estiv\infra
docker compose up -d postgres redis
```

**Atajo (Docker + migraciones en un paso):** desde `bot-estiv\` (carpeta interna con `apps\` e `infra\`):

```powershell
.\scripts\levantar-docker-y-migrar.ps1
```

Tip: si querés ver logs:

```powershell
docker compose logs -f postgres
docker compose logs -f redis
```

---

## 4) API (FastAPI) y migraciones

En una terminal:

```powershell
cd .\bot-estiv\apps\api
uv sync
uv run alembic upgrade head
uv run uvicorn bot_estiv.main:app --reload
```

Si no tenés `uv` instalado en esa PC:

```powershell
python -m pip install -U uv
```

---

## 5) Worker (ARQ)

En otra terminal:

```powershell
cd .\bot-estiv\apps\api
uv sync
uv run arq bot_estiv.schedulers.worker.WorkerSettings
```

---

## 6) Dashboard (Next.js)

En otra terminal:

```powershell
cd .\bot-estiv\apps\dashboard
npm install
npm run dev
```

Notas:

- Si preferís `pnpm`, podés usarlo, pero con `npm` alcanza.
- `NEXT_PUBLIC_API_BASE_URL` vive en `.env` (ver `bot-estiv/.env.example`).

---

## 7) Comandos Git que vas a usar siempre

### Ver estado

```powershell
git status
```

### Bajar cambios (si trabajaste desde otra PC)

```powershell
git pull
```

### Subir cambios

```powershell
git add .
git commit -m "tu mensaje"
git push
```

### Ver historial rápido

```powershell
git log --oneline --decorate -n 20
```

---

## 8) Importante (para no romper nada)

- **No versionar**: `bot-estiv/.env`, `node_modules/`, `.next/`, `.venv/` (ya están ignorados).
- La infra usa `Branding/` por rutas relativas, por eso **esta carpeta debe quedar dentro del repo** (ya lo está).

---

## 9) Producción en VPS Hostinger

La guía de producción vive en `bot-estiv/infra/DEPLOY.md`, sección **VPS Hostinger (Docker Compose + Nginx + SSL)**.

Archivos principales:

- `bot-estiv/.env.vps.example`: plantilla de variables para el VPS.
- `bot-estiv/infra/docker-compose.vps.yml`: servicios productivos con Postgres pgvector, Redis, API, worker y dashboard.
- `bot-estiv/infra/nginx/bot-estiv.conf`: reverse proxy HTTPS para dashboard y API.
- `bot-estiv/scripts/setup-hostinger-vps.sh`: prepara Ubuntu/Hostinger con Docker, Nginx, Certbot, `ufw` sin activarlo por defecto y carpetas.
- `bot-estiv/scripts/deploy-hostinger-vps.sh`: build, migraciones, arranque y certificados.
- `bot-estiv/scripts/backup-hostinger-vps.sh`, `restore-hostinger-vps.sh`, `status-hostinger-vps.sh`: operación diaria.

En el dashboard, la página **Configuración** muestra el estado de despliegue y la presencia de variables críticas sin revelar secretos.
