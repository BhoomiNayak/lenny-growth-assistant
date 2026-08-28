# The Lenny Growth Assistant — Build Plan & Kiro Methodology

> **Goal:** Build a full-stack, AI-powered conversational web app with RAG, artifact generation, and dual LLM support (cloud + local Ollama) — optimized for Kiro agentic development.

---

## Philosophy

Treat this as a **forward-deployment engagement**, not a side project. Every decision should be:
1. **Defensible** — document why you chose X over Y
2. **Observable** — logs, health checks, structured errors
3. **Handoff-ready** — a stranger can clone, run, and extend in < 10 minutes
4. **Grounded** — every answer cites Lenny's transcripts

---

## Kiro Development Methodology

### Session Strategy
Kiro works best with **bounded context windows** and **clear phase gates**. Do NOT dump the entire spec into one chat. Instead:

| Session | Focus | Input Context | Output |
|---------|-------|---------------|--------|
| **S0** | Setup & Scaffolding | `kiro-context.md` + `architecture.md` (infra section) | Project skeleton, Docker Compose, DB migrations |
| **S1** | Data Ingestion & RAG | `PRD.md` (knowledge base section) + `architecture.md` (ingestion flow) | Ingestion pipeline, chunking, vector store, source tracing |
| **S2** | Agent Layer & Skills | `PRD.md` (product tasks) + `architecture.md` (agent routing) | Claude Agent SDK setup, RAG skill, Ship 30for30 skill, artifact skill |
| **S3** | API Layer | `architecture.md` (API endpoints) + `design.md` | FastAPI routes, Pydantic models, session middleware, error handling |
| **S4** | Frontend | `design.md` (full) + `architecture.md` (API contracts) | React/Vue chat UI, artifact viewer, model toggle |
| **S5** | Resilience & Observability | `PRD.md` (risks) + `architecture.md` (security/deploy) | Logging, health checks, graceful fallbacks, sanitization |
| **S6** | Tests & Docs | All docs | Unit tests, integration tests, manual test plan, final README |

### Kiro Prompting Patterns

**1. Context-First Prompting**
Always start a Kiro session by pasting the relevant `.md` file(s) first, then:
```
"You are building [specific component]. The full context is above. 
Constraints: [list 3-5 hard constraints]. 
Deliverable: [specific file/module]."
```

**2. Review-First Refactoring**
Before asking Kiro to "add X", ask it to:
```
"Review the current [file] for [specific quality: error handling, type safety, testability].
List 3 issues. Then fix them before adding X."
```

**3. Agent Transcript Logging**
After every significant Kiro session, save the transcript (even failures) to `/agent-transcripts/`. The evaluator wants to see your judgment in directing AI work.

**4. Checkpoint Commits**
After every session: `git add . && git commit -m "S[N]: [what was built]"`

---

## Phase-by-Phase Build Plan

### Phase 0: Discovery & Lock-In (You + Kiro, 30 min)
**Goal:** Finalize assumptions and scope before code.

- [ ] Define primary user persona (Product/Growth IC at Series A startup?)
- [ ] Lock success metric (e.g., "90% of answers cite a transcript source")
- [ ] Confirm scope exclusions (e.g., "No auth — single tenant", "No real-time transcript updates")
- [ ] Choose transcript source strategy (see `PRD.md` assumptions)
- [ ] **Deliverable:** Finalized `PRD.md`, `architecture.md`, `design.md`

### Phase 1: Foundation (Kiro Session S0)
**Goal:** A runnable skeleton with DB and API.

- [ ] Project structure (see `architecture.md`)
- [ ] `docker-compose.yml` (FastAPI + PostgreSQL + optional vector DB)
- [ ] `.env.example` with safe defaults
- [ ] FastAPI app factory with lifespan events
- [ ] SQLAlchemy/asyncpg models (Session, Message, SourceCitation)
- [ ] Alembic migrations
- [ ] Health check endpoint (`/health`)
- [ ] Structured logging setup (structlog or standard logging + JSON)
- [ ] **Deliverable:** `curl http://localhost:8000/health` returns 200

### Phase 2: Knowledge Base (Kiro Session S1)
**Goal:** Transcripts are ingested, chunked, indexed, and traceable.

- [ ] Clone transcript repo: `git clone https://github.com/ChatPRD/lennys-podcast-transcripts.git data/transcripts`
- [ ] Transcript parser: read `episodes/{guest}/transcript.md`, split YAML frontmatter from body
- [ ] Chunking logic (semantic by paragraph boundaries + token count, ~500 tokens, 50 overlap)
- [ ] Embedding generation (local: `nomic-embed-text` via Ollama; cloud: OpenAI `text-embedding-3-small`)
- [ ] pgvector storage with source tracing metadata (guest, title, youtube_url, publish_date)
- [ ] Ingestion CLI script with idempotency (upsert by `episode_id` + `chunk_index`)
- [ ] Progress logging (X of 269 episodes processed, Y total chunks)
- [ ] **Deliverable:** `python scripts/ingest_transcripts.py` runs to completion; vector search returns relevant chunks with metadata

### Phase 3: Agent Layer (Kiro Session S2)
**Goal:** Claude Agent SDK with 3 distinct skills.

- [ ] **Research Ship 30 for 30 methodology** — Read https://www.ship30for30.com/ and extract the actual writing principles (hook types, formatting rules, narrative structure). Encode these in the skill prompt, NOT as generic "write well" instructions.
- [ ] Agent SDK setup with tool use (using `anthropic` Python package with tool_use / function calling)
- [ ] **Skill 1: RAG Q&A** — retrieves chunks, synthesizes answer, cites sources as `[Source: "Title" — Guest]`
- [ ] **Skill 2: Ship 30for30 Writer** — encodes Ship 30 for 30 writing principles (hook, narrative, skimmable, takeaway), generates ~1,250 words grounded in transcripts
- [ ] **Skill 3: Artifact Generator** — generates Markdown or HTML/CSS based on conversation context
- [ ] Model configuration layer (cloud vs. local toggle via factory pattern)
- [ ] Ollama integration with health check and fallback behavior
- [ ] **Deliverable:** Can invoke each skill via API with test prompts; sources are cited correctly

### Phase 4: API Layer (Kiro Session S3)
**Goal:** RESTful API with sessions, persistence, and validation.

- [ ] `POST /sessions` — create chat session
- [ ] `POST /sessions/{id}/messages` — send message, route to agent, stream or sync response
- [ ] `GET /sessions/{id}/messages` — retrieve conversation history
- [ ] `GET /sessions/{id}/artifacts` — list generated artifacts
- [ ] `GET /artifacts/{id}` — retrieve specific artifact
- [ ] Pydantic request/response models with strict validation
- [ ] Structured error responses (HTTP status + error code + message + retryable flag)
- [ ] Session context injection (last N messages as conversation memory)
- [ ] **Deliverable:** Full API testable via Swagger UI

### Phase 5: Frontend (Kiro Session S4)
**Goal:** Polished chat UI with artifact viewer.

- [ ] Tech choice: React + Vite (or Next.js if you prefer) — keep it simple
- [ ] Chat interface (message list, input, streaming indicators)
- [ ] Session sidebar (new chat, history list)
- [ ] **Artifact Viewer** — side panel or modal that renders Markdown/HTML safely
- [ ] Model toggle UI (visible indicator: "Running on Ollama — llama3.1" or "Claude 3.5 Sonnet")
- [ ] Source citation rendering (clickable chips/badges)
- [ ] Responsive layout (mobile: stacked, desktop: sidebar + chat + artifact panel)
- [ ] Accessibility (ARIA labels, keyboard nav, focus management)
- [ ] **Deliverable:** Can chat, see sources, toggle model, view artifacts

### Phase 6: Resilience & Observability (Kiro Session S5)
**Goal:** Production-grade handling of failure modes.

- [ ] Missing API keys → graceful degradation to local model
- [ ] Ollama unavailable → clear error + fallback to cloud
- [ ] Model timeout → configurable timeout with user-friendly message
- [ ] Empty retrieval results → "I don't have enough context on that..."
- [ ] DB connection failure → retry with exponential backoff + health check failure
- [ ] Artifact sanitization (DOMPurify-like logic or iframe sandbox)
- [ ] Structured logs for: model calls, retrieval latency, token usage, errors
- [ ] **Deliverable:** Simulate each failure mode; system handles gracefully

### Phase 7: Tests & Documentation (Kiro Session S6)
**Goal:** Evaluator can trust and extend the system.

- [ ] Unit tests: chunking, prompt builders, sanitization
- [ ] Integration tests: API endpoints with test DB
- [ ] Agent tests: skill routing, RAG grounding, artifact generation
- [ ] Manual test plan: step-by-step UI verification
- [ ] `README.md`: architecture, setup, env vars, run commands, troubleshooting
- [ ] `agent-transcripts/` folder with session logs (scrub secrets!)
- [ ] **Deliverable:** `pytest` passes, manual test plan documented

### Phase 8: Demo & Submission
**Goal:** 2-3 minute video + clean repo.

- [ ] Record demo (camera on): problem, product walkthrough, Ollama demo, trade-off explanation
- [ ] Final `git commit` and push
- [ ] Verify clean clone → `docker-compose up` works on fresh machine
- [ ] Submit form

---

## Key Technical Decisions (Lock These Early)

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| **Frontend** | React + Vite + Tailwind | Fast, familiar, no SSR complexity |
| **Vector DB** | pgvector (PostgreSQL extension) | One DB to manage, works with Supabase/Railway |
| **Embeddings** | `nomic-embed-text` (local) / `text-embedding-3-small` (cloud) | Good quality, fast, cheap |
| **Agent SDK** | Anthropic Claude Agent SDK | Required by brief; tool use is clean |
| **Local LLM** | `llama3.1:8b` or `qwen2.5:7b` via Ollama | Runs on most laptops, good enough for demo |
| **Cloud LLM** | Claude 3.5 Sonnet (via API) | Best reasoning for complex tasks |
| **Artifact Sanitization** | bleach (Python) + iframe sandbox (frontend) | Defense in depth |
| **Sessions** | UUIDv4, stored in PostgreSQL | Simple, portable |
| **Context Window** | Last 10 messages + retrieved chunks | Balance between coherence and token cost |

---

## Risk Register (Update as You Build)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hallucination despite RAG | Medium | High | Force citation requirement; return "unsure" if no chunks |
| Ollama too slow on laptop | High | Medium | Streaming responses; set expectations in UI |
| Transcript data quality poor | Medium | High | Clean ingestion pipeline; validate chunk quality |
| Artifact XSS | Low | Critical | Server-side sanitization + client-side sandbox |
| Scope creep | High | Medium | Strict phase gates; refer to `PRD.md` exclusions |

---

## Daily Kiro Ritual

1. **Morning:** Paste `kiro-context.md` + relevant phase doc into new Kiro chat
2. **Build:** Direct Kiro with specific, bounded tasks
3. **Review:** Read every line Kiro generates; question assumptions
4. **Test:** Run tests before ending session
5. **Log:** Save transcript to `/agent-transcripts/session-N.md`
6. **Commit:** `git commit` with phase tag

---

*Last updated: 2026-08-26*
*Next step: Finalize Phase 0 assumptions, then kick off S0 with Kiro.*
