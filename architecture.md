# Architecture Document
# The Lenny Growth Assistant

**Version:** 1.0  
**Date:** 2026-08-26  
**Author:** [Your Name]

---

## 1. System Overview

```
┌─────────────────┐      HTTP/WebSocket       ┌──────────────────┐
│   React Frontend│◄────────────────────────►│   FastAPI Backend│
│   (Vite + TS)   │                          │   (Python 3.11+) │
└────────┬────────┘                          └────────┬─────────┘
         │                                            │
         │    ┌──────────────┐    ┌──────────────┐   │
         └───►│ Artifact     │    │ Chat API     │◄──┘
              │ Viewer       │    │ (REST)       │
              │ (iframe)     │    └──────┬───────┘
              └──────────────┘           │
                                         ▼
┌──────────────────────┐
│  Agent Orchestrator  │
│  (custom + httpx)    │
└──────────┬───────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
           ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
           │  RAG Skill  │     │ Ship30 Skill │     │ Artifact     │
           │  (Q&A)      │     │ (Essay)      │     │ Skill        │
           └──────┬──────┘     └──────┬───────┘     └──────┬───────┘
                  │                   │                    │
                  ▼                   ▼                    ▼
           ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
           │  Retrieval  │     │  LLM         │     │  LLM         │
           │  Service    │     │  (Cloud/     │     │  (Cloud/     │
           │  (pgvector) │     │   Local)     │     │   Local)     │
           └──────┬──────┘     └──────┬───────┘     └──────┬───────┘
                  │                   │                    │
                  ▼                   ▼                    ▼
           ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
           │ PostgreSQL  │     │  Ollama      │     │  Anthropic   │
           │ + pgvector  │     │  (local)     │     │  / OpenAI    │
           │             │     │              │     │  (cloud)     │
           └─────────────┘     └──────────────┘     └──────────────┘
```

---

## 2. Database Schema

### 2.1 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────────┐
│   Session   │◄──────│   Message   │       │   Artifact      │
├─────────────┤ 1:N   ├─────────────┤       ├─────────────────┤
│ id (UUID)   │       │ id (UUID)   │       │ id (UUID)       │
│ title       │       │ session_id  │       │ session_id      │
│ created_at  │       │ role        │       │ type            │
│ updated_at  │       │ content     │       │ title           │
└─────────────┘       │ sources     │       │ content         │
                      │ created_at  │       │ sanitized       │
                      └─────────────┘       │ created_at      │
                                             └─────────────────┘
┌─────────────────┐
│  TranscriptChunk│
├─────────────────┤
│ id (UUID)       │
│ episode_id      │
│ guest           │
│ episode_title   │
│ youtube_url     │
│ publish_date    │
│ chunk_index     │
│ content         │
│ embedding       │  <-- pgvector vector(768)
│ metadata        │  <-- JSONB
└─────────────────┘
```

### 2.2 Table Definitions

#### `sessions`
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    model_provider VARCHAR(50) NOT NULL DEFAULT 'ollama',
    model_name VARCHAR(100) NOT NULL DEFAULT 'llama3.1:8b',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `messages`
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    latency_ms INTEGER,
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `artifacts`
```sql
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL CHECK (type IN ('markdown', 'html')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    sanitized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `transcript_chunks`
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id VARCHAR(100) NOT NULL,
    guest VARCHAR(200) NOT NULL,
    episode_title VARCHAR(500) NOT NULL,
    youtube_url VARCHAR(500),
    publish_date DATE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (episode_id, chunk_index)
);

CREATE INDEX idx_transcript_chunks_embedding ON transcript_chunks 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_transcript_chunks_episode ON transcript_chunks (episode_id);
```

---

## 3. API Endpoints

### 3.1 Health & Observability

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/health` | Liveness probe | `{"status": "ok", "version": "1.0.0"}` |
| GET | `/health/ready` | Readiness probe (DB, LLM) | `{"status": "ready", "dependencies": {"db": true, "ollama": true, "anthropic": false}}` |

### 3.2 Sessions

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/api/v1/sessions` | Create session | `{ "title?": "string" }` | `Session` |
| GET | `/api/v1/sessions` | List sessions | Query: `limit`, `offset` | `Session[]` |
| GET | `/api/v1/sessions/{id}` | Get session | — | `Session` |
| DELETE | `/api/v1/sessions/{id}` | Delete session | — | `204` |

### 3.3 Messages

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/api/v1/sessions/{id}/messages` | Send message | `{ "content": "string", "stream?": false }` | `Message` or SSE stream |
| GET | `/api/v1/sessions/{id}/messages` | Get messages | Query: `limit`, `offset` | `Message[]` |

**Message Schema:**
```json
{
  "id": "uuid",
  "session_id": "uuid",
  "role": "assistant",
  "content": "Airbnb improved activation by...",
  "sources": [
    {
      "episode_id": "brian-chesky",
      "guest": "Brian Chesky",
      "episode_title": "Designing a 10-star experience",
      "youtube_url": "https://youtube.com/watch?v=...",
      "publish_date": "2023-04-12",
      "excerpt": "They focused on the 'aha moment' of seeing your first booking..."
    }
  ],
  "latency_ms": 2450,
  "token_count": 342,
  "created_at": "2026-08-26T12:00:00Z"
}
```

### 3.4 Artifacts

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/api/v1/sessions/{id}/artifacts` | Generate artifact | `{ "type": "markdown|html", "prompt": "string" }` | `Artifact` |
| GET | `/api/v1/sessions/{id}/artifacts` | List artifacts | — | `Artifact[]` |
| GET | `/api/v1/artifacts/{id}` | Get artifact | — | `Artifact` |

### 3.5 Configuration

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/api/v1/config/models` | List available models | — | `{ "providers": [...], "current": "..." }` |
| PUT | `/api/v1/sessions/{id}/model` | Switch model for session | `{ "provider": "anthropic", "model": "claude-3-5-sonnet-20241022" }` | `{ "provider": "anthropic", "model": "claude-3-5-sonnet-20241022" }` |

### 3.6 Streaming (SSE) Contract

When `stream: true` is set on `POST /api/v1/sessions/{id}/messages`, the response uses Server-Sent Events:

```
Content-Type: text/event-stream

data: {"type": "start", "message_id": "uuid"}

data: {"type": "token", "content": "Airbnb "}

data: {"type": "token", "content": "focused on "}

data: {"type": "sources", "sources": [{"episode_id": "brian-chesky", "guest": "Brian Chesky", ...}]}

data: {"type": "done", "message_id": "uuid", "latency_ms": 2450, "token_count": 342}

data: {"type": "artifact", "artifact_id": "uuid", "title": "Retention Essay"}

data: {"type": "error", "code": "LLM_UNAVAILABLE", "message": "Ollama is not running"}
```

**Frontend consumption:** Use `fetch()` with `ReadableStream` (not `EventSource`) for POST support and better error handling.

---

## 4. Component Boundaries

### 4.1 Backend Layers

```
┌─────────────────────────────────────────┐
│           Router Layer                  │
│  (FastAPI routers — HTTP concerns only) │
│  - Validation (Pydantic)                │
│  - Auth (future)                        │
│  - Rate limiting (future)               │
├─────────────────────────────────────────┤
│           Service Layer                 │
│  (Business logic, orchestration)        │
│  - SessionService                       │
│  - AgentService                         │
│  - RetrievalService                     │
│  - ArtifactService                      │
├─────────────────────────────────────────┤
│           Agent Layer                   │
│  (Custom Orchestrator + httpx + Skills)│
│  - BaseAgent                            │
│  - RAGSkill                             │
│  - Ship30Skill                          │
│  - ArtifactSkill                        │
├─────────────────────────────────────────┤
│           Data Layer                    │
│  (SQLAlchemy + pgvector)                │
│  - SessionRepository                    │
│  - MessageRepository                    │
│  - ChunkRepository                      │
│  - ArtifactRepository                   │
├─────────────────────────────────────────┤
│           External Layer                │
│  - OllamaClient                         │
│  - AnthropicClient                      │
│  - OpenAIClient (embeddings)            │
└─────────────────────────────────────────┘
```

### 4.2 Dependency Flow

```
Routers ──► Services ──► Agents ──► External Clients
   │           │           │
   ▼           ▼           ▼
Repositories ◄─────────────┘
   │
   ▼
PostgreSQL
```

**Rules:**
- Routers never call Agents or External Clients directly
- Services never call External Clients directly for LLM generation (only via Agent layer)
- **Exception:** RetrievalService calls embedding clients directly (embedding is a data-layer concern, not an agent concern)
- Agents never call Repositories directly (Services pass data)
- No layer skips more than one level down (except the embedding exception above)

---

## 5. Ingestion & Retrieval Flow

### 5.1 Transcript Ingestion Pipeline

**Data Source:** `https://github.com/ChatPRD/lennys-podcast-transcripts`
- 303 episodes in `episodes/{guest-name}/transcript.md`
- YAML frontmatter: `guest`, `title`, `youtube_url`, `video_id`, `publish_date`, `description`, `duration_seconds`, `duration`, `view_count`, `channel`
- Topic index in `index/` with 50+ keyword files

```
git clone https://github.com/ChatPRD/lennys-podcast-transcripts.git data/transcripts
           │
           ▼
┌─────────────────────────────┐
│  ingest_transcripts.py      │
│  (CLI script)               │
├─────────────────────────────┤
│ 1. Walk episodes/ directory │
│ 2. Parse YAML frontmatter   │
│    (guest, title, url, date)│
│ 3. Clean transcript text    │
│ 4. Split by speaker turns   │
│ 5. Chunk (semantic)         │
│    - Target: ~500 tokens    │
│    - Overlap: 50 tokens     │
│ 6. Generate embedding       │
│    (nomic-embed-text)       │
│ 7. Upsert to pgvector       │
│    (idempotent by episode_id│
│     + chunk_index)          │
└─────────────────────────────┘
           │
           ▼
   PostgreSQL (transcript_chunks)
```

**Parsing Strategy:**
```python
import yaml
from pathlib import Path

def parse_transcript(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    parts = content.split("---")
    if len(parts) >= 3:
        frontmatter = yaml.safe_load(parts[1])
        transcript = "---".join(parts[2:]).strip()
        return {"metadata": frontmatter, "transcript": transcript}
    return {"metadata": {}, "transcript": content}
```

**Chunking Strategy:**
- Primary: Semantic chunking using paragraph boundaries + token count
- Fallback: Fixed-size (500 tokens) with 50-token overlap
- Metadata preserved per chunk: `episode_id` (derived from folder name), `guest`, `title`, `youtube_url`, `publish_date`, `chunk_index`
- Idempotency: Upsert by `(episode_id, chunk_index)` composite key — re-running ingestion skips existing chunks

### 5.2 Retrieval Flow (RAG)

```
User Query
    │
    ▼
┌─────────────────┐
│ Embed query     │
│ (nomic-embed-text)│
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Vector search   │  <-- cosine similarity, top-k=5
│ (pgvector)      │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Re-rank (optional)│
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Build context   │
│ prompt          │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ LLM generation  │
│ (Claude/Ollama) │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Parse citations │
│ Store message   │
└─────────────────┘
```

**Retrieval Prompt Template:**
```
You are The Lenny Growth Assistant. Answer the user's question using ONLY 
the provided transcript excerpts. Cite your sources inline using 
[Source: "Episode Title" — Guest Name].

If the provided excerpts don't contain enough information, say "I don't have 
enough information to answer that confidently."

Do NOT make up information. Do NOT use knowledge outside these excerpts.

Excerpts:
{retrieved_chunks}

Conversation history:
{session_context}

User: {query}
Assistant:
```

---

## 6. Agent Routing

### 6.1 Skill Router

```python
class SkillRouter:
    def route(self, message: str, session_context: list) -> Skill:
        if self._is_artifact_request(message):
            return ArtifactSkill()
        if self._is_ship30_request(message):
            return Ship30Skill()
        if self._is_content_generation_intent(message, session_context):
            return Ship30Skill()
        return RAGSkill()

    def _is_artifact_request(self, msg: str) -> bool:
        keywords = ["create html", "generate slide", "make a chart", "build a table", "artifact"]
        return any(k in msg.lower() for k in keywords)

    def _is_ship30_request(self, msg: str) -> bool:
        keywords = ["ship 30 for 30", "ship 30for30", "essay", "write an article", "blog post"]
        return any(k in msg.lower() for k in keywords)
```

### 6.2 Skill Execution Flow

```
User Message
    │
    ▼
SkillRouter.select_skill()
    │
    ├──► RAGSkill
    │      ├── Retrieve chunks
    │      ├── Build prompt
    │      ├── Call LLM
    │      └── Return answer + citations
    │
    ├──► Ship30Skill
    │      ├── Retrieve chunks (if topic provided)
    │      ├── Build Ship 30for30 prompt (with style rules)
    │      ├── Call LLM
    │      ├── Store as artifact
    │      └── Return summary + artifact_id
    │
    └──► ArtifactSkill
           ├── Build artifact prompt (with conversation context)
           ├── Call LLM
           ├── Sanitize HTML (if applicable)
           ├── Store as artifact
           └── Return artifact_id
```

---

## 7. Model Toggle Architecture

### 7.1 Configuration Layer

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    LLM_PROVIDER: Literal["ollama", "anthropic", "openai"] = "ollama"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    OPENAI_API_KEY: str | None = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    class Config:
        env_file = ".env"

settings = Settings()
```

### 7.2 Provider Factory

```python
class LLMFactory:
    @staticmethod
    def get_chat_provider(provider: str):
        if provider == "ollama":
            return OllamaChatClient()
        elif provider == "anthropic":
            return AnthropicChatClient()
        elif provider == "openai":
            return OpenAIChatClient()
        raise ValueError(f"Unknown provider: {provider}")

    @staticmethod
    def get_embedding_provider(provider: str):
        if provider == "ollama":
            return OllamaEmbeddingClient()
        return OpenAIEmbeddingClient()
```

### 7.3 Fallback Behavior

| Scenario | Behavior |
|----------|----------|
| Ollama selected but unavailable | Return 503 with message; UI prompts to switch |
| Anthropic selected but key missing | Return 503 with message; UI prompts to check env |
| Provider switch mid-session | New messages use new provider; old messages retain original provider metadata |
| Embedding model mismatch | Re-embed on first query (slow) or reject with clear error |

---

## 8. Security Architecture

### 8.1 Threat Model

| Threat | Vector | Mitigation |
|--------|--------|------------|
| XSS via artifacts | Malicious HTML in generated artifacts | Server: `bleach` sanitization; Client: iframe sandbox |
| Prompt injection | User input manipulates system prompt | Strict prompt templating; user content in `user` role only |
| Data exfiltration | Artifact contains external links/scripts | Sanitization removes `<script>`, `<form>`, `javascript:` URLs |
| Secret leakage | API keys in logs/transcripts | Pydantic Settings; log filtering; transcript scrubbing |
| SQL injection | Unsanitized query parameters | SQLAlchemy ORM only; no raw SQL |

### 8.2 Artifact Sanitization

```python
import bleach

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'div', 'span', 'table', 'thead', 
    'tbody', 'tr', 'td', 'th', 'blockquote', 'code', 'pre'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
    '*': ['class', 'style']
}

ALLOWED_STYLES = [
    'color', 'background-color', 'font-size', 'font-weight', 'text-align',
    'margin', 'padding', 'border', 'width', 'height', 'display'
]

def sanitize_html(html: str) -> str:
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        styles=ALLOWED_STYLES,
        strip=True
    )
```

### 8.3 Artifact Viewer Isolation

**Strategy: Defense in depth (sanitize + sandbox)**

1. **Server-side (bleach):** Strips `<script>`, `<form>`, `<iframe>`, `<object>`, `<embed>`, `javascript:` URLs, and event handlers (`onclick`, `onerror`, etc.)
2. **Client-side (iframe sandbox):** Renders sanitized HTML in a maximally restricted iframe

```html
<iframe
  srcDoc={sanitizedHtml}
  sandbox=""
  style="border: none; width: 100%; height: 100%;"
  title="Artifact Preview"
/>
```

**Sandbox with empty string = maximum restriction:**
- No scripts (`allow-scripts` omitted)
- No forms (`allow-forms` omitted)
- No popups (`allow-popups` omitted)
- No top-navigation (`allow-top-navigation` omitted)
- No same-origin access (`allow-same-origin` omitted)
- Treated as a unique, opaque origin

**What the viewer permits:**
- Static HTML rendering (headings, paragraphs, lists, tables, images via `src`)
- Inline CSS styling (colors, layout, typography)
- External images (via `<img src>` — allowed by default in sandboxed iframes)

**What the viewer blocks:**
- All JavaScript execution (no `<script>`, no event handlers)
- Form submission
- Popups or new windows
- Navigation of the parent page
- Access to parent frame's DOM, cookies, or storage
- Plugin content (Flash, Java, etc.)

**Why this is sufficient:** The LLM generates HTML for visual artifacts (slide decks, charts, formatted docs). These don't need interactivity. If interactive artifacts are needed in the future, we can selectively add `allow-scripts` with a user consent prompt.

---

## 9. Deployment Topology

### 9.1 Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_USER: lenny
      POSTGRES_PASSWORD: lenny
      POSTGRES_DB: lenny_assistant
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5440:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lenny"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://lenny:lenny@db:5432/lenny_assistant
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
      - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.1:8b}
      - OLLAMA_EMBEDDING_MODEL=${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-claude-3-5-sonnet-20241022}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - OPENAI_EMBEDDING_MODEL=${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}
      - CORS_ORIGINS=http://localhost:3010,http://127.0.0.1:3010
      - APP_ENV=${APP_ENV:-development}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "8001:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: >
      sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

  frontend:
    build: ./frontend
    ports:
      - "3010:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8001

volumes:
  postgres_data:
```

### 9.2 Environment Variables

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://lenny:lenny@localhost:5440/lenny_assistant

LLM_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3010,http://127.0.0.1:3010
```

### 9.3 Startup Sequence

```
1. docker-compose up
2. PostgreSQL starts, creates DB, enables pgvector
3. Backend waits for DB healthcheck
4. Alembic runs migrations
5. Backend starts FastAPI on :8001
6. Frontend starts Vite dev server on :3010
7. Evaluator opens http://localhost:3010
```

---

## 10. Observability

### 10.1 Logging Standards

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

### 10.2 Key Log Events

| Event | Fields | Level |
|-------|--------|-------|
| `api.request` | method, path, correlation_id | INFO |
| `api.response` | method, path, status, duration_ms | INFO |
| `llm.request` | provider, model, messages_count | INFO |
| `llm.response` | provider, model, duration_ms, tokens_in, tokens_out | INFO |
| `retrieval.query` | query, top_k, duration_ms | INFO |
| `retrieval.results` | query, result_count, episode_ids | DEBUG |
| `artifact.generated` | type, session_id, sanitized | INFO |
| `error` | error_type, message, stack_trace | ERROR |

### 10.3 Health Check Details

```json
{
  "status": "healthy",
  "timestamp": "2026-08-26T12:00:00Z",
  "version": "1.0.0",
  "dependencies": {
    "database": {
      "status": "connected",
      "latency_ms": 12
    },
    "ollama": {
      "status": "available",
      "models": ["llama3.1:8b", "nomic-embed-text"]
    },
    "anthropic": {
      "status": "unconfigured",
      "reason": "API key not set"
    }
  }
}
```

---

## 11. Error Handling Strategy

### 11.1 Error Taxonomy

```python
from fastapi import HTTPException

class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 500, retryable: bool = False):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(message)

class LLMUnavailableError(AppError):
    def __init__(self, provider: str):
        super().__init__(
            message=f"{provider} is currently unavailable. Please try another model.",
            code="LLM_UNAVAILABLE",
            status_code=503,
            retryable=True
        )

class RetrievalError(AppError):
    def __init__(self):
        super().__init__(
            message="Unable to search knowledge base. Please try again.",
            code="RETRIEVAL_FAILED",
            status_code=500,
            retryable=True
        )

class EmptyRetrievalError(AppError):
    def __init__(self):
        super().__init__(
            message="I don't have enough information to answer that confidently.",
            code="NO_RELEVANT_SOURCES",
            status_code=200,
            retryable=False
        )
```

### 11.2 Global Exception Handler

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.error(
        "application_error",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
        retryable=exc.retryable
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable
            }
        }
    )
```

---

*Next step: Review with Kiro in Session S0, then implement Phase 1.*
