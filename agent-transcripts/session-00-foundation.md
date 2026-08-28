# Session S0 — Foundation

**Goal:** A runnable skeleton — Docker Compose, FastAPI app factory, async SQLAlchemy
models, Alembic migrations, health endpoints, and structured logging.

## Direction Given to the Agent

> "Generate the complete FastAPI project skeleton with Docker Compose, SQLAlchemy async
> models, Alembic migrations, health endpoints, and structured logging. Follow the project
> structure in kiro-context.md exactly."

Hard constraints emphasized up front: **async everywhere** (asyncpg + AsyncSession, not
sync SQLAlchemy), **model toggle through config only** (no hardcoded model names), and
**pgvector** for embeddings.

## What Was Built

- Project structure: `backend/app/{routers,services,agents,utils}`, `frontend/`, `scripts/`, `alembic/`
- `config.py` — Pydantic Settings with `LLM_PROVIDER` toggle (ollama / anthropic / openai)
- `database.py` — async engine (pool_size=5, max_overflow=10, pool_pre_ping), `get_db` dependency
- `models.py` — `Session`, `Message`, `Artifact`, `TranscriptChunk` (SQLAlchemy 2.0 `mapped_column`)
- `schemas.py` — Pydantic v2 request/response contracts
- `main.py` — app factory, lifespan, CORS, structured exception handlers
- `routers/health.py` — `/health` (liveness) + `/health/ready` (DB, Ollama, cloud checks)
- Alembic async `env.py` + initial migration `001`
- `docker-compose.yml` — pgvector + backend + frontend

## Verification Gate

`docker compose up` → all three containers start, DB healthcheck passes, migrations run,
and `GET /health` returns `200 {"status":"ok"}`. `GET /health/ready` reported DB connected,
Ollama available, Anthropic unconfigured.

## Corrections During the Session

- **Port conflicts.** The default ports (8000/5432/3000) were already taken by another
  project on the machine (an `erp-agent` on 8000, several Postgres instances). Remapped to
  **8001 / 5440 / 3010** and updated `CORS_ORIGINS` accordingly.
- **Docker Compose `version` warning.** Removed the obsolete `version: '3.8'` key.

## Outcome

Runnable skeleton verified. `/health` green, DB migrations applied. Ready for ingestion.
