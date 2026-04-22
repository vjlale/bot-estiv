# Bot-Estiv — Guía rápida (para la PC del trabajo)

Este repo contiene:

- `bot-estiv/`: API + worker (Python/FastAPI/LangGraph) y dashboard (Next.js)
- `Branding/`: assets y manual de marca (usado por la API/infra)

---

## 1) Clonar el repo (PC del trabajo)

Abrí PowerShell en la carpeta donde querés el proyecto y corré:

```powershell
git clone https://github.com/vjlale/bot-estiv.git
cd bot-estiv
```

---

## 2) Variables de entorno (.env) — obligatorio

El repo **NO** incluye secretos. Tenés que crear tu `.env` local:

```powershell
cd .\bot-estiv
copy .\.env.example .\.env
notepad .\.env
```

- Completá credenciales (Gemini/Twilio/Meta/Figma/S3, etc.).
- **No subas** `.env` (está ignorado por Git).

---

## 3) Infra con Docker (Postgres + Redis)

Desde la raíz del repo:

```powershell
cd .\bot-estiv\infra
docker compose up -d postgres redis
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

