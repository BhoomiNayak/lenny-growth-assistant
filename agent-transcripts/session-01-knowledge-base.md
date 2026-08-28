# Session S1 — Knowledge Base (Ingestion + Retrieval)

**Goal:** Transcripts parsed, chunked, embedded, stored in pgvector, and retrievable with
source citations.

## Direction Given to the Agent

> "Build the transcript ingestion pipeline: parser, semantic chunking, embedding
> generation (nomic-embed-text via Ollama), pgvector storage with source tracing. Include
> the CLI script and idempotency logic."

**Data source:** `github.com/ChatPRD/lennys-podcast-transcripts` — 303 episode folders,
each `episodes/{guest}/transcript.md` with YAML frontmatter (guest, title, youtube_url,
publish_date, ...).

## What Was Built

- `scripts/ingest_transcripts.py` — CLI (`--data-dir`, `--limit`, `--ollama-url`,
  `--embedding-model`, `--db-url`). Pipeline: parse frontmatter → chunk (~500 tokens, 50
  overlap) → embed via Ollama → upsert to pgvector (idempotent on `episode_id + chunk_index`).
- `services/retrieval_service.py` — query embedding + cosine similarity search returning
  deduplicated `SourceCitation` objects.

## Failed Attempts & Corrections

### Attempt 1 — `expected list or ndarray`
The first upsert used SQLAlchemy `pg_insert(...).values(embedding=str(embedding))`. pgvector
rejected the stringified list. **Fix:** switched to a raw `text()` INSERT with the embedding
formatted as a pgvector literal `"[v1,v2,...]"` and `cast(:embedding as vector)`.

### Attempt 2 — `syntax error at or near ":"`
The `cast(:embedding::vector)` form failed under asyncpg (parameter binding collides with
the `::` cast). **Fix:** used `cast(:embedding as vector)` (functional form). See
[debugging-highlights.md #2](./debugging-highlights.md).

### Attempt 3 — the big one: **0 results from vector search**
Ingestion succeeded (152 chunks from 3 episodes), but retrieval returned nothing. A full
diagnostic (row count, dims, self-similarity, single-row distance, ordered vs unordered
scan) traced it to the **IVFFlat index built on an empty table** in the migration. Removed
it from the migration; the ingestion script now rebuilds it after loading data. Full
write-up in [debugging-highlights.md #1](./debugging-highlights.md).

## Verification Gate

`RetrievalService` end-to-end test: three queries ("How to build a growth team?", "What is
product-market fit?", "How do I improve retention?") each returned correctly-cited,
episode-deduplicated results with structured logging.

## Outcome

Ingestion + retrieval working. **Note:** only 3 episodes ingested during development to
validate the pipeline; full 303-episode ingestion is a separate unattended run before the
demo (the script is idempotent and safe to re-run).
