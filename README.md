# The Lenny Growth Assistant

> **Forward Deployed Engineer Take-Home Assessment**
> A full-stack, AI-powered conversational web app that turns Lenny's Podcast transcripts
> into a reliable internal assistant — grounded RAG answers, Ship 30 for 30 essays, and
> rendered Markdown/HTML artifacts, running fully local on Ollama (with an optional cloud toggle).

---

## What You Get

- **Grounded Q&A (RAG)** — answers cite the exact Lenny's Podcast episode/guest
- **Ship 30 for 30 essays** — ~1,250-word structured essays grounded in transcripts
- **Artifact generation** — Markdown & HTML, rendered in a sandboxed in-app viewer
- **Dual LLM** — local Ollama by default, switchable to Anthropic/OpenAI with no code change
- **Sessions** — independent, persisted chat histories
- **Operationally ready** — Docker Compose, structured logs, health checks, graceful failures, 66 automated tests

---

## Prerequisites

Install these before starting:

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop (with Compose) | latest | https://www.docker.com/products/docker-desktop/ |
| Ollama | latest | macOS/Linux: https://ollama.com/download · Windows: `winget install Ollama.Ollama` |
| Python | 3.11+ | Needed only to run the ingestion script from the host |
| Git | any | — |

An Anthropic or OpenAI API key is **optional** — the demo runs entirely on local Ollama.

---

## Quick Start (clone → run)

The commands below are copy-paste ready. Windows users: use the PowerShell variants where noted.

### 1. Clone the project

```bash
git clone https://github.com/BhoomiNayak/lenny-growth-assistant.git
cd lenny-growth-assistant
```

### 2. Create your .env

```bash
cp env.example .env          # macOS / Linux
```
```powershell
copy env.example .env        # Windows PowerShell
```
The defaults work as-is for a local Ollama demo. No secrets required.

### 3. Start Ollama and pull the models

Make sure the Ollama app/service is running, then:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Verify it's up: `ollama list` should show both models.

### 4. Get the transcript data (303 episodes)

```bash
git clone https://github.com/ChatPRD/lennys-podcast-transcripts.git data/transcripts
```
This lands 303 episode folders under `data/transcripts/episodes/`. (The `data/` folder is gitignored.)

### 5. Start the stack

```bash
docker compose up -d
```
This launches PostgreSQL (pgvector), the FastAPI backend, and the React frontend. On first
run the backend automatically applies database migrations.

Confirm everything is healthy:
```bash
curl http://localhost:8001/health/ready
```
You should see `"status": "ready"` with `database: connected` and `ollama: available`.

### 6. Ingest the transcripts (one-time, from the host)

The ingestion script runs on your host machine (it reaches Postgres on `localhost:5440` and
Ollama on `localhost:11434`).

```bash
pip install -r backend/requirements.txt
python scripts/ingest_transcripts.py
```

- Full run = 303 episodes and takes ~1.5–2.5 hrs on CPU (embeddings via Ollama).
- **For a faster demo**, ingest a subset: `python scripts/ingest_transcripts.py --limit 30`
- The script is idempotent — safe to re-run or resume.

### 7. Open the app

- **Frontend UI:** http://localhost:3010
- **API docs (Swagger):** http://localhost:8001/docs

Ask something like *"How do you build a high-performing growth team?"* and you'll get a
grounded answer with source citations.

---

## Ports

Remapped from defaults to avoid conflicts with other local services. Change them in
`docker-compose.yml` if needed.

| Service | Host Port | URL |
|---------|-----------|-----|
| Frontend (React/Vite) | **3010** | http://localhost:3010 |
| Backend (FastAPI) | **8001** | http://localhost:8001/docs |
| PostgreSQL (pgvector) | **5440** | `localhost:5440` |
| Ollama | **11434** | runs on host, not in Docker |

---

## Architecture Overview

```
React Frontend (Vite + TS + Tailwind)  ── http/SSE ──▶  FastAPI Backend (Python 3.11, async)
                                                          │
                        ┌─────────────────────────────────┼─────────────────────────────────┐
                        ▼                                 ▼                                 ▼
              PostgreSQL + pgvector              Agent Orchestrator                  LLM Provider Factory
              (sessions, messages,               (RAG · Ship30 · Artifact            (Ollama local  /
               artifacts, embeddings)             skills + router)                    Anthropic · OpenAI cloud)
```

Full detail — DB schema, endpoints, agent routing, model toggle, security model, deployment
topology — is in [`architecture.md`](./architecture.md).

---

## Using the Cloud LLM (optional)

By default everything runs on local Ollama. To enable a cloud provider:

1. Add your key to `.env`:  `ANTHROPIC_API_KEY=sk-ant-...`  (or `OPENAI_API_KEY=sk-...`)
2. Restart the backend:  `docker compose up -d backend`
3. In the UI, click the model pill (top-right) and select the cloud model.

Fallback behavior: if a selected provider is unavailable (Ollama down, key missing), the API
returns a structured, retryable error and the UI shows a Retry action — it never crashes.

---

## Testing

**Automated suite — 66 tests** covering API, retrieval, chunking, agent routing,
persistence, and HTML sanitization.

```bash
# One-time: create the test database
docker compose exec -T db psql -U lenny -d lenny_assistant -c "CREATE DATABASE lenny_test;"

# Run the suite inside the backend container
docker compose exec -T \
  -e TEST_DATABASE_URL="postgresql+asyncpg://lenny:lenny@db:5432/lenny_test" \
  backend python -m pytest -q
```
Expected: `66 passed`.

**Frontend type check:**
```bash
docker compose exec -T frontend npx tsc --noEmit
```

**Manual UI test plan:** [`MANUAL_TEST_PLAN.md`](./MANUAL_TEST_PLAN.md) — streaming, artifact
isolation, model toggle, resilience, responsive layout, accessibility, observability.

---

## Project Structure

```
lenny-growth-assistant/
├── docker-compose.yml       # One-command stack
├── env.example              # Copy to .env
├── README.md                # This file
├── PRD.md                   # Product requirements & discovery brief
├── architecture.md          # DB schema, API, agent routing, security, deployment
├── design.md                # UI/UX principles, states, accessibility
├── PLAN.md                  # Build methodology
├── MANUAL_TEST_PLAN.md      # Manual UI test plan
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── routers/         # sessions, messages, artifacts, config, health
│   │   ├── services/        # llm_service, retrieval_service
│   │   ├── agents/          # skill router + RAG / Ship30 / Artifact skills
│   │   ├── utils/           # logging, errors, middleware, chunking, sanitization
│   │   ├── models.py        # SQLAlchemy ORM
│   │   └── main.py          # app factory
│   ├── alembic/             # DB migrations
│   └── tests/               # pytest suite (66 tests)
├── frontend/                # React + Vite + Tailwind
│   └── src/{components,api,hooks,types}
├── scripts/
│   └── ingest_transcripts.py
├── data/transcripts/        # Cloned transcript repo (gitignored)
└── agent-transcripts/       # AI-assisted build logs (failed attempts + fixes)
```

---

## Environment Variables

Defined in `env.example`. Docker Compose injects container-appropriate values automatically;
you only edit `.env` for host-run ingestion or to add cloud keys.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | No | `ollama` | Active provider: `ollama` / `anthropic` / `openai` |
| `DATABASE_URL` | Yes | host: `...@localhost:5440/...` | Postgres connection (Compose sets the in-container value) |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | No | `llama3.1:8b` | Local chat model |
| `OLLAMA_EMBEDDING_MODEL` | No | `nomic-embed-text` | Local embedding model |
| `ANTHROPIC_API_KEY` | For Claude | — | Anthropic key (optional) |
| `ANTHROPIC_MODEL` | No | `claude-3-5-sonnet-20241022` | Claude model |
| `OPENAI_API_KEY` | For OpenAI | — | OpenAI key (optional) |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI chat model |
| `CORS_ORIGINS` | No | `http://localhost:3010,...` | Allowed frontend origins |
| `RETRIEVAL_TOP_K` | No | `5` | Chunks retrieved per query |
| `RETRIEVAL_SIMILARITY_THRESHOLD` | No | `0.5` | Minimum cosine similarity |
| `MAX_CONTEXT_MESSAGES` | No | `10` | Prior messages sent as context |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `docker compose up` can't reach Ollama | Ensure Ollama is running (`ollama serve` or the app) and models are pulled. The backend reaches host Ollama via `host.docker.internal:11434` (macOS/Windows) — set automatically. |
| Backend can't reach Ollama on **Linux** | Set `OLLAMA_BASE_URL=http://172.17.0.1:11434` in `.env` and `docker compose up -d backend`. |
| `cp env.example .env` fails on Windows | Use `copy env.example .env`. |
| Retrieval returns 0 results | Make sure ingestion has run. The IVFFlat index is built automatically at the end of an ingestion run. |
| Answers are slow (~40–50s) | Normal for an 8B model on CPU. Switch to a cloud model via the UI toggle, or use a smaller local model (`ollama pull phi3:mini`). Streaming keeps the UI responsive. |
| Frontend can't reach backend | Confirm `VITE_API_URL=http://localhost:8001` and that `8001`'s origin (`3010`) is in `CORS_ORIGINS`. |
| Port already in use | Ports are remapped (3010/8001/5440). Change them in `docker-compose.yml`. |
| Trace a request | Every response has an `X-Correlation-ID`; grep backend logs (`docker compose logs backend`) by that id. |

---

## Deliverables Map

| Deliverable | Location |
|-------------|----------|
| Source code | this repo |
| README | this file |
| PRD | [`PRD.md`](./PRD.md) |
| Design | [`design.md`](./design.md) |
| Architecture | [`architecture.md`](./architecture.md) |
| Agent transcripts | [`agent-transcripts/`](./agent-transcripts/) |
| Tests | `backend/tests/` + [`MANUAL_TEST_PLAN.md`](./MANUAL_TEST_PLAN.md) |

---

*Built with the Kiro coding agent. See [`agent-transcripts/`](./agent-transcripts/) for the
real build journey, including failed attempts and how they were corrected.*
