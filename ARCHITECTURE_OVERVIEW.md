# The Lenny Growth Assistant — Architectural Overview

> A full-stack, AI-powered conversational web app that turns Lenny's Podcast transcripts into a grounded RAG assistant with Ship 30for30 essay generation, HTML/Markdown artifact rendering, and dual LLM support (local Ollama + optional cloud).

---

## 1. Directory Tree & File Inventory

```
lennys_rag/
├── docker-compose.yml              # One-command stack: db, backend, frontend
├── env.example                     # Host-run env config (copy to .env)
├── README.md                       # Setup guide, ports, troubleshooting
├── PRD.md                          # Product requirements, user flows, success metrics
├── design.md                       # UI/UX spec: layout, states, accessibility, tokens
├── architecture.md                 # DB schema, API contracts, layer boundaries, security
├── PLAN.md                         # Kiro methodology + phase-gated build plan
├── kiro-context.md                 # Prime document for Kiro agent sessions
├── MANUAL_TEST_PLAN.md             # 10-section UI test checklist
├── .gitignore                      # Ignores data/, .env, venvs, __pycache__
├── backend/                        # FastAPI application
│   ├── Dockerfile                  # Python 3.11-slim, uvicorn entrypoint
│   ├── requirements.txt            # 37 dependencies (FastAPI, SQLAlchemy, httpx, bleach, etc.)
│   ├── pytest.ini                  # asyncio_mode=auto, testpaths=tests
│   ├── alembic.ini                 # Alembic config
│   ├── alembic/
│   │   ├── env.py                  # Async SQLAlchemy migration runner
│   │   ├── script.py.mako          # Migration template with pgvector import
│   │   └── versions/
│   │       └── 001_initial_schema.py  # Creates 4 tables + vector extension
│   ├── app/
│   │   ├── __init__.py             # Package marker (empty)
│   │   ├── main.py                 # FastAPI app factory: middleware, CORS, error handlers, routers
│   │   ├── config.py               # Pydantic Settings — all env vars, provider toggle, computed props
│   │   ├── database.py             # asyncpg engine, session factory, get_db dependency, wait_for_db retry
│   │   ├── models.py               # SQLAlchemy ORM: Session, Message, Artifact, TranscriptChunk
│   │   ├── schemas.py              # Pydantic I/O schemas (21 models including StreamEvent)
│   │   ├── routers/
│   │   │   ├── __init__.py         # Package marker (empty)
│   │   │   ├── health.py           # /health (liveness) + /health/ready (dependency readiness)
│   │   │   ├── sessions.py         # CRUD sessions: POST/GET/PATCH/DELETE /api/v1/sessions
│   │   │   ├── messages.py         # Send message (sync + SSE stream), list history
│   │   │   ├── artifacts.py        # Generate, list, get artifacts
│   │   │   └── config.py           # List providers + switch session model
│   │   ├── services/
│   │   │   ├── __init__.py         # Package marker (empty)
│   │   │   ├── llm_service.py      # LLMService: unified Ollama/Anthropic/OpenAI client (sync + stream)
│   │   │   └── retrieval_service.py # RetrievalService: embedding gen + pgvector cosine search
│   │   ├── agents/
│   │   │   ├── __init__.py         # Package marker (empty)
│   │   │   ├── base.py             # AgentOrchestrator + SkillRouter (intent → skill dispatch)
│   │   │   ├── skills/
│   │   │   │   ├── __init__.py     # Package marker (empty)
│   │   │   │   ├── rag_skill.py    # Grounded Q&A with inline citations
│   │   │   │   ├── ship30_skill.py # Ship 30for30 essay writer (~1,250 words, structured markdown)
│   │   │   │   └── artifact_skill.py# Markdown/HTML document generator + bleach sanitization
│   │   │   └── tools/
│   │   │       └── __init__.py     # Package marker (empty, reserved for MCP-style tools)
│   │   └── utils/
│   │       ├── __init__.py         # Package marker (empty)
│   │       ├── logging.py          # structlog JSON (prod) / console (dev) with contextvars
│   │       ├── errors.py           # AppError hierarchy (12 exception classes, structured codes)
│   │       ├── middleware.py       # RequestLoggingMiddleware: correlation IDs + timing
│   │       └── chunking.py         # parse_transcript + chunk_text (shared, unit-tested)
│   └── tests/
│       ├── __init__.py             # Package marker (empty)
│       ├── conftest.py             # Fixtures: test engine, db_session, client, sample_chunk, FakeLLMResponse
│       ├── test_api.py             # Health, sessions, messages, config endpoints (10 tests)
│       ├── test_retrieval.py       # Chunking, parsing, vector search, citation conversion (14 tests)
│       ├── test_agent_routing.py   # SkillRouter routing + topic extraction (9 tests)
│       ├── test_persistence.py     # ORM CRUD + cascade delete + defaults (7 tests)
│       └── test_sanitization.py    # HTML sanitization (XSS vectors) + title extraction (12 tests)
├── frontend/                       # React + Vite + Tailwind
│   ├── Dockerfile                  # node:20-alpine dev server
│   ├── package.json                # React 18, Vite 5, Tailwind 3, lucide-react, react-markdown
│   ├── package-lock.json           # Locked dependencies
│   ├── vite.config.ts              # Host 0.0.0.0:3000, vitest jsdom test config
│   ├── tsconfig.json               # Strict TS, noUnusedLocals, noUnusedParameters
│   ├── tailwind.config.js          # Extends primary color palette
│   ├── postcss.config.js           # tailwindcss + autoprefixer
│   ├── index.html                  # Root HTML, Inter font
│   └── src/
│       ├── main.tsx                # ReactDOM.createRoot with StrictMode
│       ├── App.tsx                 # Root component: state management, routing, SSE streaming
│       ├── index.css               # Tailwind directives + Google Fonts import
│       ├── vite-env.d.ts           # ImportMetaEnv type for VITE_API_URL
│       ├── test-setup.ts           # @testing-library/jest-dom + scrollIntoView mock
│       ├── types/
│       │   └── index.ts            # Shared TypeScript interfaces (Session, Message, Artifact, etc.)
│       ├── api/
│       │   └── client.ts           # fetch wrapper: REST + SSE streaming, error parsing
│       └── components/
│           ├── SessionSidebar.tsx  # New chat, session list, delete with confirm
│           ├── MessageList.tsx     # Message bubbles, markdown render, typing indicator
│           ├── MessageInput.tsx    # Auto-resize textarea, Cmd+Enter send
│           ├── SourceCitation.tsx  # Clickable source chips with excerpt tooltips
│           ├── ModelToggle.tsx     # Dropdown model/provider selector (green/blue color coding)
│           ├── ArtifactViewer.tsx  # Tabbed artifact panel with iframe sandbox + markdown render
│           ├── ModelToggle.test.tsx # Vitest: renders, dropdown, switch behavior (4 tests)
│           └── MessageList.test.tsx# Vitest: renders messages, typing indicator, stream (3 tests)
├── scripts/
│   └── ingest_transcripts.py       # CLI: parse → chunk → embed → upsert → rebuild IVFFlat index
├── data/transcripts/               # Cloned repo (gitignored): 269 episode transcripts + 50 topic index
│   ├── README.md                   # Archive description, format spec, project showcase list
│   ├── scripts/build-index.sh      # Claude CLI topic-index generator (idempotent)
│   └── index/                      # 50+ topic keyword files (ab-testing.md, ai.md, leadership.md, ...)
└── agent-transcripts/              # Kiro session logs (build journey, failures, fixes)
    ├── README.md                   # Index of sessions 00–07
    ├── session-00-foundation.md    # Phase 0: PRD, architecture, design lock-in
    ├── session-01-knowledge-base.md
    ├── session-02-agent-layer.md
    ├── session-03-api-layer.md
    ├── session-04-frontend.md
    ├── session-05-security-review.md
    ├── session-06-resilience.md
    ├── session-07-tests.md
    └── debugging-highlights.md     # Key failures and corrections during build
```

### Key File Summaries

| File | One-Sentence Summary |
|------|---------------------|
| `backend/app/main.py` | Application factory: registers middleware, CORS, exception handlers, and all routers into a single FastAPI instance |
| `backend/app/config.py` | Central `Settings` singleton (Pydantic) reading all env vars; exposes `current_model_name`, `is_cloud_provider`, `cors_origins_list` |
| `backend/app/database.py` | Async SQLAlchemy engine (pool_size=5, pre_ping, 300s recycle), `get_db` dependency, `wait_for_db` exponential-backoff retry |
| `backend/app/models.py` | Four ORM models: Session (1:N messages/artifacts), Message (JSONB sources), Artifact (markdown/html flag), TranscriptChunk (Vector(768) + JSONB metadata) |
| `backend/app/schemas.py` | 21 Pydantic models covering all request/response contracts including the SSE `StreamEvent` type with 6 event types |
| `backend/app/routers/messages.py` | Message endpoint with dual-mode: sync JSON response or 5-phase SSE streaming with DB session release during LLM wait |
| `backend/app/routers/sessions.py` | Session CRUD with pagination (limit/offset), auto-title from first message content |
| `backend/app/routers/artifacts.py` | Artifact generation via ArtifactSkill, list by session, get by ID |
| `backend/app/routers/config.py` | Probes Ollama availability via httpx, reports Anthropic/OpenAI key status, switches per-session model |
| `backend/app/routers/health.py` | `/health` liveness (always 200), `/health/ready` checks DB + Ollama + cloud provider with latency |
| `backend/app/services/llm_service.py` | LLMService facade with `_generate_*` / `_stream_*` for Ollama, Anthropic (streaming SSE parsing), OpenAI; 300s timeout |
| `backend/app/services/retrieval_service.py` | RetrievalService: `_generate_embedding` (Ollama or OpenAI), `_vector_search` (pgvector cosine, raw SQL), `get_context_for_query` (formats context + deduplicates citations) |
| `backend/app/agents/base.py` | `SkillRouter` (keyword-based intent detection) + `AgentOrchestrator` (routes to skills, handles both sync and stream paths) |
| `backend/app/agents/skills/rag_skill.py` | RAGSkill: retrieves top-k chunks, builds grounded system prompt, calls `llm.generate` or `generate_stream`, returns answer + citations |
| `backend/app/agents/skills/ship30_skill.py` | Ship30Skill: ~1,250-word essay with Ship 30for30 methodology (hook → problem → insight → evidence → takeaway) |
| `backend/app/agents/skills/artifact_skill.py` | ArtifactSkill: generates Markdown or self-contained HTML, 2-stage sanitization (regex strip dangerous blocks + bleach allowlist + CSSSanitizer) |
| `backend/app/utils/errors.py` | 12 exception classes (AppError base, LLMUnavailable, LLMTimeout, RetrievalError, EmptyRetrieval, SessionNotFound, ArtifactNotFound, ValidationError, DatabaseError) |
| `backend/app/utils/middleware.py` | RequestLoggingMiddleware: X-Correlation-ID propagation, structlog contextvars binding, request/response timing |
| `backend/app/utils/logging.py` | structlog config: JSONRenderer in prod, ConsoleRenderer in dev; stdlib handler integration; noisy loggers quieted |
| `backend/app/utils/chunking.py` | `parse_transcript` (YAML frontmatter split) + `chunk_text` (paragraph-boundary chunking, 500 tokens, 50 overlap) — shared by ingestion & tests |
| `scripts/ingest_transcripts.py` | Idempotent ingestion: walks episodes/, parses YAML, chunks, batch-embeds via Ollama, upserts by (episode_id, chunk_index), rebuilds IVFFlat index at end |
| `frontend/src/App.tsx` | Root component: manages sessions, messages, artifacts, streaming state, model config; orchestrates SSE stream consumption |
| `frontend/src/api/client.ts` | Type-safe API client: `request<T>` helper + REST functions + `sendMessageStream` (fetch + ReadableStream + SSE line parser) |
| `frontend/src/components/ModelToggle.tsx` | Dropdown pill showing provider/model, color-coded (green=local, blue=cloud), disabled state for unconfigured providers |
| `frontend/src/components/ArtifactViewer.tsx` | Right-panel artifact view: tab switching, sandboxed iframe for HTML, ReactMarkdown for markdown, copy/download actions |
| `backend/alembic/versions/001_initial_schema.py` | Creates pgvector extension, uuid-ossp, 4 tables, indexes; deliberately defers IVFFlat index to post-ingestion |

---

## 2. Component Architecture & Workflow

### 2.1 Layer Diagram

```
┌─────────────────────────────────────────────┐
│              React Frontend                  │
│         (Vite + TS + Tailwind)               │
│                                              │
│  App.tsx (root)                              │
│    ├── api/client.ts (fetch + SSE)           │
│    ├── types/index.ts (shared interfaces)    │
│    └── components/                           │
│        ├── SessionSidebar.tsx                │
│        ├── MessageList.tsx (+ typing dots)   │
│        ├── MessageInput.tsx (Cmd+Enter)      │
│        ├── SourceCitation.tsx (chips)        │
│        ├── ModelToggle.tsx (dropdown)        │
│        └── ArtifactViewer.tsx (iframe)       │
└──────────────────┬──────────────────────────┘
                   │ HTTP/SSE (port 8001→3010)
┌──────────────────┴──────────────────────────┐
│              FastAPI Backend                │
│         (Python 3.11, async)                │
│                                              │
│  main.py  ──►  Routers  ──►  Services  ──►  Agents  ──►  External
│  (factory)       (HTTP)      (logic)      (skills)      (LLM/API)
└─────────────────────────────────────────────┘
                   │
                   ▼
       PostgreSQL + pgvector (port 5440→5432)
```

### 2.2 Backend Layer Boundaries (Enforced)

The architecture document (`architecture.md:282-299`) defines strict dependency rules:

```
Routers  ──►  Services  ──►  Agents  ──►  External Clients (Ollama/Anthropic/OpenAI)
   │           │            │
   ▼           ▼            ▼
Repositories ◄──────────────┘
   │
   ▼
PostgreSQL
```

| Layer | Responsibility | Never Touches |
|-------|---------------|---------------|
| **Routers** (`app/routers/`) | HTTP validation (Pydantic), dependency injection, response shaping | Agents, External Clients directly |
| **Services** (`app/services/`) | Business logic orchestration, DB access, embedding calls | External LLM clients directly (except embeddings) |
| **Agents** (`app/agents/`) | Skill routing, prompt construction, LLM orchestration | Repositories directly |
| **Data** (`app/database.py`, `models.py`) | Async SQLAlchemy, ORM models, connection pool | — |
| **External** | httpx clients to Ollama/anthropic.com/api.openai.com | — |

**Exception:** `RetrievalService` calls embedding providers directly — embedding generation is treated as a data-layer concern, not an agent concern.

### 2.3 Data Model (4 Tables)

Defined in `backend/app/models.py` with matching migration in `001_initial_schema.py`:

```
┌─────────────────┐       ┌──────────────┐
│   Session       │ 1 ──* │   Message    │
├─────────────────┤       ├──────────────┤
│ id (UUID)       │       │ id (UUID)    │
│ title           │       │ session_id FK│
│ model_provider  │       │ role         │
│ model_name      │       │ content      │
│ created_at      │       │ sources JSONB│
│ updated_at      │       │ latency_ms   │
└─────────────────┘       │ token_count  │
                          │ created_at   │
                          └──────────────┘

┌─────────────────┐       ┌──────────────────┐
│   Artifact      │       │  TranscriptChunk |
├─────────────────┤       ├──────────────────┤
│ id (UUID)       │       │ id (UUID)        │
│ session_id FK   │       │ episode_id       │
│ type (md/html)  │       │ guest            │
│ title           │       │ episode_title    │
│ content         │       │ chunk_index      │
│ sanitized       │       │ content          │
│ created_at      │       │ embedding vec    │
└─────────────────┘       │ metadata JSONB   │
                          └──────────────────┘
```

- **Cascade delete:** Deleting a Session removes all associated Messages and Artifacts (ORM `cascade="all, delete-orphan"` + DB `ON DELETE CASCADE`)
- **Idempotency:** `transcript_chunks` has a `UNIQUE(episode_id, chunk_index)` constraint; ingestion uses `ON CONFLICT DO UPDATE`
- **Vector search:** IVFFlat index on `embedding` column — intentionally not created in the migration (empty-table centroids are degenerate); built by `ingest_transcripts.py:274-299` after data loads

### 2.4 Execution Flow: Streaming Message (the Core Path)

**Entrypoint:** `POST /api/v1/sessions/{id}/messages` with `stream: true` → `messages.py:send_message()`

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Save user message (short-lived DB session)         │
│  ─ db.get(Session) → verify exists                          │
│  ─ read session.model_provider, model_name                  │
│  ─ db.add(Message(role=user)) → db.commit()                 │
│  ─ session closed (connection returned to pool)             │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Load session context (short-lived DB session)      │
│  ─ SELECT last 10 messages ORDER BY created_at DESC         │
│  ─ Reverse to chronological order                          │
│  ─ session closed                                            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Pre-retrieve RAG context (short-lived DB session)  │
│  ─ AgentOrchestrator.router.route() → "rag"/"ship30"/       │
│    "artifact"                                                │
│  ─ For RAG: retrieval.get_context_for_query(query)          │
│    → embed query (Ollama/OpenAI) → vector search (pgvector)   │
│    → format context text + deduplicate SourceCitations      │
│  ─ For Ship30: same but topic extracted + top_k=8            │
│  ─ session closed — DB pool free BEFORE LLM streaming        │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Stream LLM tokens (no DB session held)            │
│  ─ yield {"type":"start","message_id":uuid}                 │
│  ─ agent.process_message_stream() dispatches to skill:      │
│    • RAGSkill.answer_stream() → retrieval + llm.generate_   │
│      stream() → yield token per chunk                       │
│    • Ship30Skill.generate_essay_stream() → same pattern     │
│    • ArtifactSkill: NOT streamed (needs sanitization) →     │
│      full response at once                                 │
│  ─ yield {"type":"token","content":"..."} per token          │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: Save assistant message (short-lived DB session)    │
│  ─ yield {"type":"sources","sources":[...]}                  │
│  ─ db.add(Message(role=assistant, sources_jsonb,             │
│    latency_ms, token_count))                                 │
│  ─ If artifact generated: db.add(Artifact(...))              │
│  ─ Auto-title session if ≤2 messages (content[:50])        │
│  ─ db.commit()                                               │
│  ─ yield {"type":"done","latency_ms":N}                      │
└─────────────────────────────────────────────────────────────┘
```

**Key design decision:** The SSE handler (`_stream_response` in `messages.py:158-296`) intentionally uses **three separate short-lived DB sessions** rather than holding one connection for the entire 40–50s LLM generation. This prevents connection-pool exhaustion when many users stream simultaneously.

### 2.5 Skill Routing Logic

`SkillRouter.route()` in `agents/base.py:65-82` uses keyword matching:

1. **Artifact** — matches `ARTIFACT_KEYWORDS` (create/generate html, slide, presentation, markdown document, build a table, chart, export as, download as)
2. **Ship30** — matches `SHIP30_KEYWORDS` (ship 30 for 30, write an essay, write a blog post, write an article, turn this into an essay)
3. **RAG** — default fallback for all questions

Artifact type detection (`detect_artifact_type`) checks for `["html", "slide", "presentation", "chart", "visual", "styled"]` → html; otherwise markdown.

### 2.6 Model Toggle Flow

1. **Static config** — `LLM_PROVIDER` env var selects the default provider (`config.py:31`)
2. **Per-session override** — `PUT /api/v1/sessions/{id}/model` updates `session.model_provider` + `session.model_name` (persists in DB)
3. **Runtime injection** — `AgentOrchestrator(db, provider=session.model_provider, model=session.model_name)` passed to `LLMService`
4. **Frontend** — `ModelToggle` dropdown calls `api.switchSessionModel()`, updates local state immediately (optimistic)
5. **Health check** — `/health/ready` pokes Ollama via httpx and checks API key presence

### 2.7 Security: Defense-in-Depth for Artifacts

**Three layers** (defined in `architecture.md:582-619` + `artifact_skill.py:167-206`):

| Layer | Location | Mechanism |
|-------|----------|-----------|
| **1. Content removal** | `artifact_skill.py:184-194` | Regex strips `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<form>`, `<noscript>` — including inner content |
| **2. Allowlist sanitization** | `artifact_skill.py:196-203` | `bleach.clean()` with 27 allowed tags, attribute allowlist, `CSSSanitizer` for style properties |
| **3. Client-side sandbox** | `ArtifactViewer.tsx:128-133` | `<iframe sandbox="" srcDoc={sanitizedHtml}>` — empty sandbox attribute = maximum restriction (no scripts, no forms, no popups, no top-nav, no same-origin) |

### 2.8 Deployment Topology

`docker-compose.yml:1-61` defines three services:

- **db** — `ankane/pgvector:latest` on port 5440, healthcheck with `pg_isready`
- **backend** — `python:3.11-slim`, depends on db healthy, runs `alembic upgrade head` then `uvicorn app.main:app` with `--reload`
- **frontend** — `node:20-alpine`, Vite dev server on port 3010, `VITE_API_URL=http://localhost:8001`
- **Ollama** — runs on host, backend reaches it via `host.docker.internal:11434` (macOS/Windows) or `172.17.0.1` (Linux, set in `.env`)

---

## 3. Developer Navigation Map

### Where to Make Changes: Feature-to-File Guide

#### **A. Change what the AI assistant knows / how it answers**

| Task | File(s) | Details |
|------|---------|---------|
| Change the RAG system prompt | `backend/app/agents/skills/rag_skill.py:14-25` | `SYSTEM_PROMPT` string — edit grounding rules, citation format, tone |
| Adjust retrieval (top-k, similarity threshold) | `backend/app/config.py:51-53` | `RETRIEVAL_TOP_K` (default 5), `RETRIEVAL_SIMILARITY_THRESHOLD` (default 0.5) |
| Change embedding model | `backend/app/config.py:34-36` | `OLLAMA_EMBEDDING_MODEL` or `OPENAI_EMBEDDING_MODEL` |
| Change the Ship30 essay style/methodology | `backend/app/agents/skills/ship30_skill.py:21-57` | `SYSTEM_PROMPT` — hooks, structure, formatting rules, word count |
| Add a new artifact type | `backend/app/agents/skills/artifact_skill.py` + `schemas.py:104` | Extend `ArtifactCreate.type` Literal, add system prompt, extend `_extract_title` |

#### **B. Add a new API endpoint**

| Task | File(s) | Pattern |
|------|---------|---------|
| Add a new REST route | `backend/app/routers/<name>.py` + `backend/app/main.py:122-128` | Create `APIRouter(prefix=...)`, define endpoints with `Depends(get_db)`, register in `create_app()` |
| Add a new schema (req/resp) | `backend/app/schemas.py` | Add Pydantic model, extend existing `Literal` types if adding enum values |
| Add a new DB table | `backend/app/models.py` + `backend/alembic/versions/` | Add ORM model on `Base`, create new Alembic migration file |

#### **C. Change LLM provider integration**

| Task | File(s) | Details |
|------|---------|---------|
| Add a new LLM provider | `backend/app/services/llm_service.py` | Add `_generate_<provider>` and `_stream_<provider>` methods; extend dispatch in `generate()` and `generate_stream()` |
| Change default provider | `backend/app/config.py:31` | `LLM_PROVIDER` default |
| Change cloud model name | `backend/app/config.py:40,44` | `ANTHROPIC_MODEL`, `OPENAI_MODEL` |
| Change local model name | `backend/app/config.py:35` | `OLLAMA_MODEL` |
| Adjust LLM timeout | `backend/app/services/llm_service.py:19` | `LLM_TIMEOUT = 300.0` |
| Adjust temperature / max_tokens | `rag_skill.py:67,114`, `ship30_skill.py:99,142`, `artifact_skill.py:91` | Per-skill defaults in `llm.generate()` / `llm.generate_stream()` calls |

#### **D. Modify streaming behavior / SSE events**

| Task | File(s) | Details |
|------|---------|---------|
| Add a new SSE event type | `backend/app/schemas.py:207-218` (StreamEvent) + `frontend/src/types/index.ts:79-90` | Extend the `Literal` union, add any new fields; update `handleSend` in `App.tsx` |
| Change streaming DB session strategy | `backend/app/routers/messages.py:158-296` | The 5-phase flow (save user → load context → pre-retrieve → stream → save assistant) |
| Change how context is loaded | `backend/app/routers/messages.py:193-204` | Last 10 messages via `limit(10).order_by(created_at.desc)` |

#### **E. Modify frontend UI / components**

| Task | File(s) | Details |
|------|---------|---------|
| Change chat layout (sidebar/chat/artifact) | `frontend/src/App.tsx` | Root component manages all state; 3 main sections are conditional |
| Add a new message type display | `frontend/src/components/MessageList.tsx` | `MessageBubble` renders user (right) vs assistant (left) |
| Change the input box behavior | `frontend/src/components/MessageInput.tsx` | Auto-resize textarea, Cmd+Enter hotkey, disabled state |
| Modify source citations UI | `frontend/src/components/SourceCitation.tsx` | Chips with expand-on-click, YouTube link, max 3 visible + "+N more" |
| Change artifact rendering | `frontend/src/components/ArtifactViewer.tsx` | HTML → `<iframe sandbox="">`; Markdown → `ReactMarkdown`; copy/download buttons |
| Update TypeScript types | `frontend/src/types/index.ts` | Mirror the Pydantic schemas in `backend/app/schemas.py` |
| Change API URL / env | `frontend/.env` or `docker-compose.yml:58` | `VITE_API_URL=http://localhost:8001` |

#### **F. Change database schema**

| Task | File(s) | Details |
|------|---------|---------|
| Add a column to an existing table | `backend/app/models.py` + new alembic migration | Edit model, create `backend/alembic/versions/002_*.py` with `op.add_column()` |
| Add a new table | `backend/app/models.py` + new alembic migration | Define model class inheriting `Base`, write migration `op.create_table()` |
| Change vector dimensions | `backend/app/config.py:51` | `EMBEDDING_DIMENSION` (must match embedding model output — 768 for nomic-embed-text) |

#### **G. Modify ingestion pipeline**

| Task | File(s) | Details |
|------|---------|---------|
| Change chunking parameters | `backend/app/utils/chunking.py:13-15` | `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`, `CHAR_PER_TOKEN=4` |
| Add metadata fields per chunk | `backend/app/utils/chunking.py` + `scripts/ingest_transcripts.py:72-116` | Extend `upsert_chunks` SQL, update model `metadata` field |
| Use a different embedding model | `backend/app/config.py:36` | `OLLAMA_EMBEDDING_MODEL` |
| Change batch size | `scripts/ingest_transcripts.py:35` | `BATCH_SIZE = 20` |
| Disable IVFFlat index rebuild | `scripts/ingest_transcripts.py:277-299` | Remove the index rebuild block (skipped if `total_chunks == 0`) |

#### **H. Add tests**

| Task | File(s) | Pattern |
|------|---------|---------|
| Test a backend endpoint | `backend/tests/test_api.py` | Use `client` fixture (AsyncClient with ASGITransport), assert status codes + JSON |
| Test retrieval / vector search | `backend/tests/test_retrieval.py` | Use `db_session` + `sample_chunk` fixtures, mock `_generate_embedding` |
| Test agent routing logic | `backend/tests/test_agent_routing.py` | Instantiate `SkillRouter` directly, parametrize keyword inputs |
| Test DB persistence / cascades | `backend/tests/test_persistence.py` | Use `db_session` fixture, commit + refresh, verify cascade deletes |
| Test HTML sanitization | `backend/tests/test_sanitization.py` | Instantiate `ArtifactSkill(LLMService(...))`, call `_sanitize_html` with XSS payloads |
| Test a frontend component | `frontend/src/components/<name>.test.tsx` | Use `render` + `screen` from @testing-library/react, `vitest` |

#### **I. Add error handling / new error type**

| Task | File(s) | Pattern |
|------|---------|---------|
| Add a new error class | `backend/app/utils/errors.py` | Subclass `AppError`, set `code`, `status_code`, `retryable` |
| Register a new exception handler | `backend/app/main.py:99-115` | Extend `unhandled_error_handler` or add `@app.exception_handler(NewError)` |
| Raise an error from a router | Any router | `raise SessionNotFoundError(str(session_id))` — caught by global handler in `main.py:79` |

#### **J. Modify deployment / Docker**

| Task | File(s) | Details |
|------|---------|---------|
| Change container ports | `docker-compose.yml:11,35,51` | db: 5440→5432, backend: 8001→8000, frontend: 3010→3000 |
| Add environment variable to backend | `docker-compose.yml:23-34` + `env.example` | Add to `environment:` block AND `env.example` for host use |
| Change frontend API URL | `docker-compose.yml:58` | `VITE_API_URL=http://localhost:8001` |
| Add a startup command | `docker-compose.yml:43-44` | Modify the `command: >` block (currently: alembic upgrade head + uvicorn) |

### Quick File Lookup by Concern

| Concern | Primary File | Key Lines |
|---------|-------------|-----------|
| App entrypoint | `backend/app/main.py:50-130` | `create_app()` factory |
| Config / env vars | `backend/app/config.py:12-83` | `Settings` class + `settings` singleton |
| DB models | `backend/app/models.py:29-139` | 4 ORM classes |
| Skill routing | `backend/app/agents/base.py:42-90` | `SkillRouter` + `AgentOrchestrator.__init__` |
| Streaming orchestration | `backend/app/routers/messages.py:158-296` | `_stream_response` 5-phase flow |
| SSE event contract | `backend/app/schemas.py:207-218` | `StreamEvent` model |
| Vector search SQL | `backend/app/services/retrieval_service.py:153-168` | Raw SQL with `<=>` cosine distance |
| HTML sanitization | `backend/app/agents/skills/artifact_skill.py:167-206` | Two-stage regex + bleach |
| Error taxonomy | `backend/app/utils/errors.py:8-118` | 12 exception classes |
| Frontend state | `frontend/src/App.tsx:11-337` | All useState hooks |
| Frontend API calls | `frontend/src/api/client.ts` | 8 exported functions |
| Frontend types | `frontend/src/types/index.ts` | 9 interfaces |
| DB migrations | `backend/alembic/versions/001_initial_schema.py` | Single migration |
| Ingestion CLI | `scripts/ingest_transcripts.py:177-316` | `main()` with argparse |

---

## 4. Operational Reference

### 4.1 Running Tests

```bash
# Backend: 66 tests (API, retrieval, routing, persistence, sanitization)
docker compose exec -T db psql -U lenny -d lenny_assistant -c "CREATE DATABASE lenny_test;"
docker compose exec -T \
  -e TEST_DATABASE_URL="postgresql+asyncpg://lenny:lenny@db:5432/lenny_test" \
  backend python -m pytest -q

# Frontend type check
docker compose exec -T frontend npx tsc --noEmit
```

### 4.2 Quick Start (Local)

```bash
cp env.example .env
ollama pull llama3.1:8b && ollama pull nomic-embed-text
git clone https://github.com/ChatPRD/lennys-podcast-transcripts.git data/transcripts
docker compose up -d
curl http://localhost:8001/health/ready
pip install -r backend/requirements.txt
python scripts/ingest_transcripts.py --limit 30  # or omit --limit for all 269 episodes
# Frontend: http://localhost:3010  |  API docs: http://localhost:8001/docs
```

### 4.3 Correlation ID Tracing

Every request gets an `X-Correlation-ID` (from `RequestLoggingMiddleware` at `middleware.py:32`) bound to structlog contextvars. All logs within that request include `correlation_id`. The same ID is echoed in the response header — grep backend logs by it to trace a full request lifecycle.

### 4.4 Ports

| Service | Host | Container | Notes |
|---------|------|-----------|-------|
| Frontend | 3010 | 3000 | Vite dev server |
| Backend | 8001 | 8000 | uvicorn |
| PostgreSQL | 5440 | 5432 | pgvector |
| Ollama | 11434 | host | Not in Docker |

---

## 5. Interview Prep: Feature Implementation Guides

> The following sections map common interview tasks to exact file locations and implementation steps. **No changes are made to source code here** — these are preparation references.

### 5.1 Add an API Endpoint (FastAPI route + Pydantic model + service call + response)

**Goal:** Add `POST /api/v1/sessions/{id}/feedback` to collect user thumbs-up/down on assistant responses.

**Files to touch (in order):**

1. **Schema** — `backend/app/schemas.py`
   - Add `FeedbackCreate` (Pydantic model): `thumbs: Literal["up", "down"]`, `message_id: uuid.UUID`
   - Add `FeedbackResponse`: `id`, `message_id`, `thumbs`, `created_at`

2. **DB model** — `backend/app/models.py:29-110`
   - Add `Feedback(Base)` ORM model: `session_id FK`, `message_id FK`, `thumbs`, `created_at`
   - Add `relationship` backref on `Message` if bidirectional access needed

3. **Migration** — `backend/alembic/versions/002_feedback_table.py` (new file, copy pattern from `001_initial_schema.py`)
   - `op.create_table("feedback", ...)` with `session_id` → `sessions.id` FK, `message_id` → `messages.id` FK

4. **Service** (optional, if logic >5 lines) — `backend/app/services/` (new file or extend existing)
   - If no service exists yet, create `feedback_service.py` with a `record_feedback()` method

5. **Router** — `backend/app/routers/feedback.py` (new file, copy pattern from `sessions.py:27`)
   - `APIRouter(prefix="/api/v1", tags=["feedback"])`
   - `async def record_feedback(message_id, body: FeedbackCreate, db=Depends(get_db))`
   - Validate message exists → instantiate service → return `FeedbackResponse`

6. **Register router** — `backend/app/main.py:118-128`
   - Add `from app.routers.feedback import router as feedback_router`
   - Add `app.include_router(feedback_router)`

7. **Frontend** (optional) — `frontend/src/types/index.ts` + `frontend/src/api/client.ts` + component
   - Add `Feedback` interface, `recordFeedback()` API function, thumbs-up/down UI in `MessageList.tsx`

**Key pattern reference:** `sessions.py:31-45` (POST handler), `main.py:124-128` (registration), `schemas.py:30-34` (request model pattern).

---

### 5.2 Modify RAG Retrieval (top_k, similarity threshold, no-results handling)

**Goal:** Increase retrieval recall and add empty-result feedback.

**Files to touch:**

1. **`backend/app/config.py:51-53`**
   - Change `RETRIEVAL_TOP_K` from `5` → `8` (more context per query)
   - Change `RETRIEVAL_SIMILARITY_THRESHOLD` from `0.5` → `0.4` (looser match)

2. **`backend/app/services/retrieval_service.py**
   - **Line 84-85:** `top_k` and `similarity_threshold` are read from `settings` — changing config values propagates automatically
   - **Line 65-102:** `search()` method — add handling for `len(results) == 0`:
     ```python
     if not results:
         logger.warning("retrieval.empty", query=query[:100])
         return []
     ```
   - **Line 197-228:** `get_context_for_query()` — already returns `("", [])` on empty. To surface a user-facing message instead, raise `EmptyRetrievalError` (defined in `errors.py:62-71`) so the global handler in `main.py:79-97` returns a structured 200 response.

3. **`backend/app/routers/messages.py:213-217`** — streaming path retrieves context differently for RAG vs Ship30 (uses `top_k=8` for ship30). Adjust here if needed.

4. **`backend/app/agents/skills/rag_skill.py:49-61`** — `answer()` method already checks `if not context_text` and returns a fallback message. To make no-results an explicit error instead, raise `EmptyRetrievalError` there.

**Key locations to read:**
- Vector search SQL: `retrieval_service.py:153-168` — cosine distance via `embedding <=> cast(:embedding as vector)`
- Retrieval config defaults: `config.py:51-53`
- Empty-results fallback message: `rag_skill.py:52-61` and `ship30_skill.py:83-93`

---

### 5.3 Debug Missing Citations (Systematic Debugging Flow) ⭐

**Scenario:** User asks a question, but the assistant's response has no source citation chips. Follow this 6-step diagnostic flow:

#### Step 1: Check Retrieval — `retrieval_service.py:65-102`

**Verify embedding generation and vector search return results:**
```bash
# Check if data was ingested
psql -h localhost -p 5440 -U lenny -d lenny_assistant -c "SELECT count(*) FROM transcript_chunks;"
# Check if IVFFlat index exists (needed for performance at scale)
psql -h localhost -p 5440 -U lenny -d lenny_assistant -c "\d transcript_chunks"
```
- If `count(*)` is 0 → ingestion hasn't run. Run `python scripts/ingest_transcripts.py`
- If index is missing → search will be slow (sequential scan) but still functional
- If `count(*)` is non-zero but search returns 0 → similarity threshold too high (Step 2)

**Debug command:** Lower the threshold temporarily in `config.py:53` to `0.0` to see if ANY results come back.

#### Step 2: Check Similarity Scores — `retrieval_service.py:142-195`

**Examine raw cosine similarity values:**
- The SQL at `retrieval_service.py:153-168` computes `1 - (embedding <=> cast(:embedding as vector)) as similarity`
- Log similarity values: add temporary logging in `search()` at `retrieval_service.py:95-100`:
  ```python
  for r in results:
      logger.debug("retrieval.result", episode=r.episode_id, similarity=r.similarity)
  ```
- If all similarities are below `RETRIEVAL_SIMILARITY_THRESHOLD` (default 0.5) → results get filtered out
- **Fix:** Lower `RETRIEVAL_SIMILARITY_THRESHOLD` in `config.py:53`, or use a better embedding model

#### Step 3: Check the RAG Prompt — `rag_skill.py:14-25`

**Verify the system prompt instructs citation:**
- `SYSTEM_PROMPT` at `rag_skill.py:14-25` requires: "Cite your sources inline using [Source: 'Episode Title' — Guest Name]"
- If the prompt was edited to remove citation instructions → LLM won't cite
- The user prompt at `rag_skill.py:138-146` includes `TRANSCRIPT EXCERPTS:` — verify these are populated

**Debug:** Add a log of the LLM prompt at `rag_skill.py:69-73`:
```python
logger.debug("rag_skill.prompt", messages=messages)  # Careful — may log secrets
```

#### Step 4: Check LLM Output — `App.tsx:166-209`

**Verify the frontend receives and displays citations:**
- In `App.tsx:166-176`, the `sendMessageStream` callback handles `event.type === 'sources'`
- If the LLM output has no citations but the `event.type === 'sources'` events are arriving, the issue is in LLM response parsing
- **Check:** The citations come from `_stream_response` in `messages.py:246-248`, which reads `done_citations` from the skill's final yield
- If `citations` is empty at `messages.py:247` → the skill didn't return them

#### Step 5: Check Citation Parser — `rag_skill.py:76, 119`

**Verify citations are returned from the skill:**
- In `rag_skill.py:109-119` (`answer_stream`), the final yield is `("", True, citations)` — `citations` comes from `self.retrieval.get_context_for_query(query)` at line 98
- If `context_text` is non-empty but `citations` is empty → check `get_context_for_query` at `retrieval_service.py:197-228`:
  - Citations are deduplicated by `episode_id` (`retrieval_service.py:222-225`)
  - If all results have the same `episode_id`, only 1 citation is returned — this is correct behavior, not a bug

**Debug:** Log citations in the stream path at `messages.py:247`:
```python
logger.info("stream.citations", count=len(citations))
```

#### Step 6: Check Frontend Response Handling — `frontend/src/api/client.ts:58-101`

**Verify the SSE parser extracts source events:**
- `sendMessageStream` at `client.ts:58-101` parses `data: {...}` lines
- The `sources` event is parsed at `client.ts:90-98` → `JSON.parse(line.slice(6))`
- In `App.tsx:167-176`, check `event.type === 'sources' && event.sources` — if `event.sources` is undefined, the SSE payload from `messages.py:248` may be malformed

**Common failure: JSON serialization** — `messages.py:248`:
```python
yield f"data: {json.dumps({'type': 'sources', 'sources': [c.model_dump() for c in citations]})}\n\n"
```
If `SourceCitation.model_dump()` produces unexpected field names vs the frontend type at `types/index.ts:19-26`, the frontend won't render them.

#### Full Debug Checklist

| Check | File | What to verify |
|-------|------|----------------|
| Data exists | `scripts/ingest_transcripts.py:254` | `SELECT count(*) FROM transcript_chunks` > 0 |
| Embedding model loaded | `config.py:34-36` | `OLLAMA_EMBEDDING_MODEL` is running |
| Embedding matches DB | `retrieval_service.py:104-113` | Query embedding dimensionality = 768 |
| Threshold too high | `config.py:53` | `RETRIEVAL_SIMILARITY_THRESHOLD` ≤ typical similarity |
| Context formatted | `retrieval_service.py:212-227` | `context_parts` non-empty when results found |
| Citations returned | `retrieval_service.py:222-225` | `citations` list populated before yield at `rag_skill.py:119` |
| SSE event sent | `messages.py:247-248` | `json.dumps` produces valid JSON with `sources` key |
| Frontend callback | `App.tsx:171-172` | `event.type === 'sources'` branch sets `sources` variable |
| Sources attached | `App.tsx:188-192` | `assistantMsg` includes `sources` field |
| Component renders | `SourceCitation.tsx:13` | `sources` array non-empty → chips render |

---

### 5.4 Add Regenerate Message Feature

**Goal:** Allow users to click a "Regenerate" button on an assistant message, which resends the previous user query through the agent using a different model, and appends the new response instead of overwriting history.

**Files to touch:**

1. **Schema** — `backend/app/schemas.py:69-73`
   - `MessageCreate` already supports `stream` — add optional `model_provider` and `model` fields if the API should accept a model override per-request (or reuse the session's current model)

2. **Router** — `backend/app/routers/messages.py:32-68` (`send_message`)
   - Add a query param: `regenerate: bool = Query(False)` or a body flag in `MessageCreate`
   - When `regenerate=True`:
     - Look up the previous assistant turn and its user query (`messages.py:90-100` shows how to load last 10 messages)
     - Extract the original user query: `messages[-2].content` (user message preceding the assistant's last response)
     - Pass the query to the agent with a model override if specified
   - **Append vs overwrite:** The current flow at `messages.py:112-136` saves a new assistant `Message` record. Since each regenerate creates a new `Message` row with `role="assistant"`, history grows — this is already append behavior. Just ensure the new message gets its own `id`.

3. **Agent model override** — `backend/app/agents/base.py:96-98`
   - `AgentOrchestrator.__init__` accepts `provider` and `model` params → already supported
   - Caller at `messages.py:103-107` passes `provider=session.model_provider, model=session.model_name`
   - For regenerate: pass the alternative model. The session's `model_provider`/`model_name` can be updated via `PUT /api/v1/sessions/{id}/model` (in `config.py:76-113`) first, then the existing flow will use it.

4. **Frontend** — `frontend/src/components/MessageList.tsx:54-89`
   - Add a "Regenerate" button in the assistant message bubble (below the content)
   - On click: call a new API endpoint or reuse `sendMessage` with a `regenerate` flag
   - Optimistic UI: show a loading state, then append the new assistant message

5. **API client** — `frontend/src/api/client.ts`
   - Add `regenerateMessage(sessionId, messageId, options?)` function
   - Or extend `sendMessage` to accept `{ content, stream, regenerate: true }`

**Key insight:** The current architecture already appends messages (each API call creates a new `Message` row). "Append instead of overwrite" is the **default behavior** — no history wiping occurs. The main change is: (a) extracting the previous user query, (b) optionally switching the model, (c) adding a frontend UI button.

**Files for model switch on regenerate:**
- API endpoint already exists: `PUT /api/v1/sessions/{id}/model` at `config.py:76-113`
- Frontend toggle already exists: `ModelToggle.tsx` → `App.tsx:116-127` (`handleSwitchModel`)
- For regenerate, switch model → call `switchSessionModel` → then call `sendMessageStream`

---

### 5.5 Rate Limiting (Redis vs In-Memory)

**Goal:** Limit each session/IP to N requests per minute to prevent abuse.

**Why Redis (not in-memory dict) for production:**

An in-memory dictionary (`dict[str, int]` in Python) is **process-local** — it only tracks requests handled by the *current* backend process. In production with multiple backend instances (e.g., 3 containers behind a load balancer), each instance has its own independent dict. A user could send 3x the rate limit by hitting different instances, and the limits would never aggregate. Redis is a shared, external store — all instances read/write the same counters, so rate limiting is globally consistent.

**Implementation files:**

1. **Dependencies** — `backend/requirements.txt:28-32`
   - Add `redis==5.0.7` and `slowapi==0.1.9` (or `starlette-limiter`)

2. **Redis config** — `backend/app/config.py:12-83`
   - Add `REDIS_URL: str = "redis://localhost:6379/0"` and `RATE_LIMIT_PER_MINUTE: int = 20`

3. **Middleware** — `backend/app/utils/middleware.py:21-69`
   - Add a new `RateLimitMiddleware` class (or use `slowapi`'s `Limiter`):
     ```python
     from slowapi import Limiter
     from slowapi.util import get_remote_address
     limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
     ```
   - Register on the app in `main.py:62-63` alongside `RequestLoggingMiddleware`

4. **Router-level decorators** — `backend/app/routers/messages.py:32`
   - @limiter.limit("10/minute") on `send_message`
   - @limiter.limit("5/minute") on streaming sends (more expensive)

5. **Error response** — `backend/app/utils/errors.py:8-118`
   - Add `RateLimitExceededError(AppError)` with `code="RATE_LIMITED"`, `status_code=429`
   - Register handler in `main.py:99-115`

6. **Docker Compose** — `docker-compose.yml:3-16`
   - Add a `redis:` service:
     ```yaml
     redis:
       image: redis:7-alpine
       ports: ["6379:6379"]
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
    ```

7. **Frontend** — `frontend/src/App.tsx:166-209`
   - Handle HTTP 429: show "Rate limited, try again in N seconds" error banner
   - Read `Retry-After` header from 429 response at `client.ts:21-26`

**Key file locations:**
- Middleware pattern: `middleware.py:21-69` (RequestLoggingMiddleware is the template)
- App registration: `main.py:62-63`
- Error handler pattern: `main.py:99-115` (unhandled_error_handler)
- Env var pattern: `config.py:12-19` (Settings class)
- Docker service pattern: `docker-compose.yml:3-16` (db service)

---

### 5.6 Quick Decision Matrix

| Scenario | If X, do Y at file:line |
|----------|------------------------|
| Retrieval returns 0 results | Lower `RETRIEVAL_SIMILARITY_THRESHOLD` at `config.py:53` |
| Citations missing in frontend | Check SSE `sources` event at `messages.py:247` → `App.tsx:171` → `SourceCitation.tsx:13` |
| LLM hallucinating (no grounding) | Tighten `SYSTEM_PROMPT` at `rag_skill.py:14-25` |
| IVFFlat index missing | Run ingestion at `ingest_transcripts.py:274-299` (builds post-load) |
| Model not switching in UI | Check `PUT /sessions/{id}/model` at `config.py:76-113` + `App.tsx:116-127` |
| Artifact XSS concern | Verify 3-layer defense: `artifact_skill.py:184-206` → `ArtifactViewer.tsx:128-133` |
| Streaming hangs | Check DB session release at `messages.py:206-218` (must close before LLM stream) |
| Connection pool exhausted | Each streaming request holds pool — verify short-lived sessions at `messages.py:42-57, 175-222, 251-286` |
