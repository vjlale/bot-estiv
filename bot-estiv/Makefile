# Atajos de desarrollo para Bot Estiv

.PHONY: up down logs migrate ingest fetch-templates preview-templates dev-api dev-worker dev-dash test

up:
	cd infra && docker compose up -d postgres redis

down:
	cd infra && docker compose down

logs:
	cd infra && docker compose logs -f

migrate:
	cd apps/api && uv run alembic upgrade head

ingest:
	cd apps/api && uv run python -m bot_estiv.rag.ingest

fetch-templates:
	cd apps/api && uv run python -m bot_estiv.tools.figma_sync

preview-templates:
	cd apps/api && uv run python scripts/preview_templates.py

dev-api:
	cd apps/api && uv run uvicorn bot_estiv.main:app --reload --port 8000

dev-worker:
	cd apps/api && uv run arq bot_estiv.schedulers.worker.WorkerSettings

dev-dash:
	cd apps/dashboard && pnpm dev

test:
	cd apps/api && uv run pytest
