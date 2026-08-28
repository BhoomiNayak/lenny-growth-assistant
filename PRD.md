# Product Requirements Document (PRD)
# The Lenny Growth Assistant

**Version:** 1.0  
**Date:** 2026-08-26  
**Author:** [Your Name]  
**Status:** Draft — pending Phase 0 lock-in

---

## 1. Discovery Brief

### 1.1 User and Problem

**Primary User:** Product and Growth practitioners at early-to-mid-stage startups (Series A–C). They are individual contributors or leads who need to make high-stakes decisions quickly with limited resources.

**Job to be done:** When facing a product or growth challenge (e.g., "How do I improve activation?", "What onboarding flow works best?"), they want reliable, actionable guidance grounded in real-world experience — not generic blog posts or unverified opinions.

**Pain the assistant removes:**
- **Time waste:** Searching through 200+ podcast episodes and newsletter archives manually
- **Unreliable sources:** Generic advice that doesn't account for their stage or context
- **No synthesis:** Even if they find relevant episodes, they must manually connect dots across interviews
- **No reusable output:** They can't easily turn insights into shareable documents for their team

**Secondary User:** Growth/content leads who need to produce written content (essays, strategy docs) grounded in credible sources for their team or audience.

### 1.2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Source Grounding Rate** | ≥ 90% of answers cite at least one transcript source | Log analysis + manual spot-check |
| **User Satisfaction (implicit)** | ≤ 5% "I don't know" rate on relevant PM/growth questions | Agent logs |
| **Artifact Utility** | Generated artifacts are opened/viewed in 80%+ of sessions where offered | Frontend analytics |
| **Operational Uptime** | 99.5% health check success during evaluation | `/health` endpoint monitoring |
| **Setup Time** | Fresh evaluator clones and runs in < 10 minutes | Stopwatch test |

### 1.3 Assumptions

Because the client brief was incomplete, the following assumptions were made and documented:

| # | Assumption | Rationale | Risk if Wrong |
|---|-----------|-----------|---------------|
| A1 | **Transcripts are sourced from the public ChatPRD/lennys-podcast-transcripts GitHub repo** — 303 episodes in Markdown with YAML frontmatter (guest, title, youtube_url, publish_date, duration). Organized as `episodes/{guest-name}/transcript.md`. | The assessment references "Lenny's Podcast / Newsletter transcript repository" — this is the canonical community archive. | If the repo is removed or restructured, we retain a local copy in `data/transcripts/`. |
| A2 | **Single-tenant, no authentication required** — the evaluator runs this locally. | Brief implies internal tool for a product/growth team, not a SaaS product. | If multi-tenancy is needed, we must add auth (OAuth2/API keys) post-MVP. |
| A3 | **No real-time transcript updates** — knowledge base is static at deployment, refreshed manually. | Building a live ingestion pipeline is out of scope for a take-home. | If freshness is critical, we add a webhook/cron job later. |
| A4 | **"Ship 30 for 30" style means:** ~1,250 words, strong hook, narrative arc, skimmable formatting, specific takeaway, grounded in sources. | Based on Ship 30 for 30 public methodology. | If style expectations differ, we adjust the skill prompt. |
| A5 | **Local demo machine has 16GB+ RAM and a modern CPU** — Ollama with 8B parameter models runs comfortably. | Standard developer laptop spec. | If evaluator has less RAM, we document lighter model options (`phi3:mini`). |
| A6 | **Evaluator has Docker, Docker Compose, and Ollama installed** — or is willing to install them. | Standard forward-deployed engineer toolchain. | We provide native setup instructions as fallback. |
| A7 | **Grounding means citation, not quotation** — answers should reference episode/guest/timestamp, not necessarily quote verbatim. | More natural conversational flow. | If verbatim quotes required, we adjust RAG prompt. |
| A8 | **We ingest all 303 episodes** — the full ChatPRD archive is small enough (~50-100MB text) to process in a single ingestion run. | Maximizes knowledge coverage for the evaluator demo. | If too slow, we can ingest a subset of 30-50 high-relevance episodes. |

### 1.4 Scope Choices

**Included (In Scope):**
- FastAPI backend with async PostgreSQL persistence
- Claude Agent SDK with 3 distinct skills (RAG Q&A, Ship 30for30 writer, Artifact generator)
- Dual LLM support (Ollama local + Claude cloud) with runtime toggle
- Vector search over transcript chunks with source citation
- React frontend with chat, session management, artifact viewer
- Docker Compose deployment
- Structured logging, health checks, graceful error handling
- Comprehensive test suite (automated + manual)

**Intentionally Excluded (Out of Scope):**
- User authentication / authorization (single tenant)
- Real-time transcript ingestion / sync
- Multi-modal support (audio, video, images)
- Advanced analytics dashboard
- Slack/Discord bot integrations
- Rate limiting / billing
- CI/CD pipeline (GitHub Actions)
- Multi-language support (English only)

**Rationale for exclusions:** These are valuable but not core to the "reliable internal assistant" brief. They add operational complexity without demonstrating the key evaluation criteria (RAG grounding, agent skills, artifact generation, deployment readiness).

### 1.5 Risks and Trade-offs

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Hallucination** | High | Strict RAG prompt requiring citations; return "unsure" when retrieval confidence is low; limit LLM creativity temperature |
| **Latency (Ollama)** | Medium | Streaming responses; clear UI indicators; document hardware requirements; allow cloud fallback |
| **Cost (Cloud LLM)** | Low | Local-first default; cloud only when explicitly toggled; token usage logging |
| **Local Model Quality** | Medium | Use best-in-class 8B model (`llama3.1:8b` or `qwen2.5:7b`); accept that complex reasoning may be weaker than cloud |
| **Data Leakage** | Low | No user data leaves local machine unless cloud LLM is explicitly toggled; no telemetry |
| **Unsafe Artifact Rendering** | High | Server-side HTML sanitization (`bleach`); client-side iframe sandbox; CSP headers |
| **Scope Creep** | Medium | Phase-gated plan; reference this PRD before adding features |

**Key Trade-off:** We chose pgvector over a dedicated vector DB (Pinecone/Weaviate) to reduce operational complexity. Trade-off: slightly lower ANN performance at scale, but for <10k chunks PostgreSQL with pgvector is sufficient and simplifies deployment.

---

## 2. User Flows

### Flow 1: Grounded Q&A
```
1. User opens app → sees empty chat with welcome message
2. User types: "How did Airbnb improve their activation rate?"
3. System retrieves relevant transcript chunks (e.g., Brian Chesky interview)
4. Agent synthesizes answer with inline citations
5. User sees answer + clickable source chips ("Brian Chesky — Designing a 10-star experience")
6. User asks follow-up: "What specific onboarding tactic did they use?"
7. System uses session context + new retrieval to answer
```

### Flow 2: Ship 30for30 Content Generation
```
1. User asks a question and gets a grounded answer
2. User says: "Turn this into a Ship 30for30 essay"
3. System invokes Ship 30for30 skill with conversation context
4. Agent generates ~1,250 word Markdown essay with hook, headings, bullets, takeaway
5. Essay appears in chat + as artifact in sidebar
6. User clicks artifact → sees formatted preview in Artifact Viewer
7. User can copy Markdown or download as .md file
```

### Flow 3: Artifact Generation
```
1. User says: "Create an HTML slide deck summarizing our conversation"
2. System invokes Artifact skill with full conversation context
3. Agent generates self-contained HTML/CSS snippet
4. System sanitizes HTML server-side
5. Frontend renders in sandboxed iframe in Artifact Viewer
6. User can view full-screen or copy raw HTML
```

### Flow 4: Model Toggle
```
1. User notices model indicator in header: "Running on Ollama — llama3.1"
2. User clicks toggle → dropdown shows available models
3. User selects "Claude 3.5 Sonnet"
4. System validates API key → switches provider for subsequent messages
5. Indicator updates: "Running on Anthropic — Claude 3.5 Sonnet"
```

---

## 3. Functional Requirements

### 3.1 Session Management
- **FR-S1:** Users can create a new chat session with one click
- **FR-S2:** Each session maintains independent conversation context (last 10 messages)
- **FR-S3:** Sessions are persisted in PostgreSQL with UUID, title, created_at, updated_at
- **FR-S4:** Users can view and switch between past sessions in sidebar
- **FR-S5:** Sessions can be deleted (soft delete recommended)

### 3.2 Conversational Assistant
- **FR-C1:** System accepts text messages via API
- **FR-C2:** System retrieves top-5 relevant transcript chunks per query
- **FR-C3:** System synthesizes answer grounded strictly in retrieved chunks
- **FR-C4:** Answers include source citations (episode, timestamp, speaker)
- **FR-C5:** System handles follow-up questions using session context
- **FR-C6:** System responds "I don't have enough information" when retrieval is empty or irrelevant
- **FR-C7:** System supports streaming responses for better perceived latency

### 3.3 Ship 30for30 Skill
- **FR-30-1:** Skill can be triggered explicitly ("Write a Ship 30for30 essay on X") or implicitly from conversation context
- **FR-30-2:** Output is ~1,250 words (± 10%)
- **FR-30-3:** Output includes: strong hook, narrative progression, skimmable formatting, specific takeaway
- **FR-30-4:** All claims are grounded in transcript knowledge base with citations
- **FR-30-5:** Output is valid Markdown
- **FR-30-6:** Generated essay is stored as an artifact linked to the session

### 3.4 Artifact Generation
- **FR-A1:** System can generate Markdown documents
- **FR-A2:** System can generate self-contained HTML/CSS snippets
- **FR-A3:** Artifacts are stored in PostgreSQL with metadata (type, title, created_at)
- **FR-A4:** HTML artifacts are sanitized server-side before storage
- **FR-A5:** Frontend renders HTML in sandboxed iframe with `sandbox=""` (no forms, no popups)
- **FR-A6:** Markdown artifacts are rendered with a safe markdown parser (no raw HTML injection)
- **FR-A7:** User can view, copy, and download artifacts

### 3.5 Model Configuration
- **FR-M1:** System reads LLM provider from environment variable `LLM_PROVIDER`
- **FR-M2:** UI displays current provider and model name
- **FR-M3:** User can switch provider via UI (if multiple configured)
- **FR-M4:** System gracefully handles missing API keys (clear error, suggest local model)
- **FR-M5:** System gracefully handles unavailable Ollama (clear error, suggest cloud model)
- **FR-M6:** Embedding model switches with LLM provider

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-P1:** API response time < 2s for simple queries (cloud LLM)
- **NFR-P2:** API response time < 15s for complex queries (local LLM, streaming)
- **NFR-P3:** Vector search < 500ms for 10k chunks
- **NFR-P4:** Frontend Time to Interactive < 3s on 4G

### 4.2 Reliability
- **NFR-R1:** Health check endpoint returns 200 when all dependencies healthy
- **NFR-R2:** System degrades gracefully when LLM is unavailable
- **NFR-R3:** System retries DB connections with exponential backoff
- **NFR-R4:** No data loss on unexpected shutdown (transactions)

### 4.3 Security
- **NFR-S1:** No secrets in code or logs
- **NFR-S2:** All user input validated (Pydantic)
- **NFR-S3:** HTML artifacts sanitized before storage and rendering
- **NFR-S4:** CORS restricted to frontend origin
- **NFR-S5:** No SQL injection (ORM only)

### 4.4 Observability
- **NFR-O1:** All API requests logged with correlation ID
- **NFR-O2:** LLM calls logged with model, provider, latency, token usage
- **NFR-O3:** Retrieval operations logged with query, top-k results, latency
- **NFR-O4:** Errors logged with stack traces (server-side only)
- **NFR-O5:** Health endpoint exposes dependency status (DB, Ollama, Cloud API)

### 4.5 Accessibility
- **NFR-A1:** Keyboard-navigable chat interface
- **NFR-A2:** ARIA labels on all interactive elements
- **NFR-A3:** Color contrast WCAG AA minimum
- **NFR-A4:** Focus indicators visible

---

## 5. Acceptance Criteria

### AC1: End-to-End Grounded Q&A
Given the app is running with ingested transcripts  
When I ask "What growth strategy did Figma use early on?"  
Then I receive an answer that cites at least one transcript source  
And the source includes guest name, episode title, and links to YouTube

### AC2: Follow-up Context
Given I have an active session with previous Q&A about Figma  
When I ask "How does that compare to Notion's approach?"  
Then the agent understands "that" refers to Figma's strategy  
And provides a comparative answer with sources

### AC3: Ship 30for30 Essay
Given I have a conversation about retention strategies  
When I request "Write a Ship 30for30 essay on retention"  
Then I receive a ~1,250 word Markdown document  
With a hook, headings, bullets, bold emphasis, and specific takeaway  
And all claims cite transcript sources

### AC4: Artifact Viewer Security
Given an artifact contains HTML with a `<script>alert('xss')</script>`  
When the artifact is rendered in the viewer  
Then the script is sanitized/removed  
And the artifact renders safely

### AC5: Model Toggle
Given Ollama is running locally  
When I start the app  
Then the default provider is Ollama  
And I can toggle to Claude 3.5 Sonnet  
And subsequent messages use the selected provider

### AC6: Graceful Degradation
Given Ollama is not running  
When I send a message with provider set to Ollama  
Then I receive a clear error: "Local model unavailable. Switch to cloud?"  
And the system does not crash

### AC7: Fresh Clone Setup
Given a fresh machine with Docker and Docker Compose  
When I clone the repo and run `docker-compose up`  
Then the app starts, DB migrations run, and I can access the UI at `http://localhost:3000`

---

## 6. Implementation Plan (High-Level)

| Phase | Duration | Key Deliverables | Dependencies |
|-------|----------|------------------|--------------|
| Phase 0 | 30 min | Finalized PRD, architecture, design docs | None |
| Phase 1 | 2-3 hrs | Docker Compose, FastAPI scaffold, DB models, health check | Phase 0 |
| Phase 2 | 3-4 hrs | Transcript ingestion, chunking, embeddings, pgvector | Phase 1 |
| Phase 3 | 4-5 hrs | Agent SDK, 3 skills, model toggle, Ollama integration | Phase 2 |
| Phase 4 | 3-4 hrs | API routes, session management, message persistence | Phase 3 |
| Phase 5 | 4-5 hrs | React frontend, chat, artifact viewer, model toggle UI | Phase 4 |
| Phase 6 | 2-3 hrs | Error handling, resilience, observability, sanitization | Phase 5 |
| Phase 7 | 2-3 hrs | Tests, docs, agent transcripts | Phase 6 |
| Phase 8 | 1-2 hrs | Demo video, final verification, submission | Phase 7 |

**Total estimated effort:** 22-30 hours of focused work

---

## 7. Open Questions

1. ~~What is the exact source of Lenny's transcripts?~~ **RESOLVED:** Using `ChatPRD/lennys-podcast-transcripts` GitHub repo (303 episodes, Markdown + YAML frontmatter).
2. Does the evaluator expect real-time streaming responses or are synchronous responses acceptable? **Decision:** Implement streaming (SSE) — it's expected for a polished chat UX and handles local model latency gracefully.
3. Should the Ship 30for30 skill be triggered by explicit user request only, or can the agent proactively suggest it? **Decision:** Explicit trigger only. Proactive suggestions feel intrusive for an MVP.

---

*Next step: Resolve open questions in Phase 0, then proceed to Phase 1.*
