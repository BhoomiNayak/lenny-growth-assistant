# Agent Transcripts

This folder documents the AI-assisted development of **The Lenny Growth Assistant**,
built with the Kiro coding agent. Per the assessment's deliverable #6, it includes the
real build journey — **failed attempts, the debugging that followed, and how each issue
was corrected** — not a sanitized after-the-fact narrative.

## How This Project Was Built

The work was organized into bounded sessions (S0–S6), each with a clear deliverable and
a verification gate before moving on. Every session started by priming the agent with
project context (`kiro-context.md`) plus the relevant design/architecture doc, then
directing it toward a specific, testable outcome.

| Session | Focus | Transcript |
|---------|-------|------------|
| S0 | Foundation — Docker, FastAPI, DB, migrations, health | [session-00-foundation.md](./session-00-foundation.md) |
| S1 | Knowledge base — ingestion + retrieval | [session-01-knowledge-base.md](./session-01-knowledge-base.md) |
| S2 | Agent layer — RAG, Ship 30, Artifact skills | [session-02-agent-layer.md](./session-02-agent-layer.md) |
| S3 | API routes — sessions, messages, artifacts, streaming | [session-03-api-layer.md](./session-03-api-layer.md) |
| S4 | Frontend — chat UI, artifact viewer, model toggle | [session-04-frontend.md](./session-04-frontend.md) |
| Review | Security review — 7 findings + fixes | [session-05-security-review.md](./session-05-security-review.md) |
| S5 | Resilience & observability | [session-06-resilience.md](./session-06-resilience.md) |
| S6 | Tests & documentation | [session-07-tests.md](./session-07-tests.md) |

## Notable Bugs Caught & Corrected

The most instructive moments are collected in
[debugging-highlights.md](./debugging-highlights.md). Summary:

1. **IVFFlat index built on an empty table** — retrieval returned 0 results despite 152
   valid embeddings. Root cause was a pgvector gotcha, not a threshold/normalization issue.
2. **asyncpg cannot bind `:param::vector`** — required switching to `CAST(:param AS vector)`.
3. **Ollama 500 on large prompts** — `num_predict` option caused failures; fixed with `num_ctx`.
4. **Bleach kept `<script>` inner text** — `strip=True` removed tags but left the payload text.
5. **Bleach `styles=` was the wrong parameter** — CSS sanitizer silently ignored; corrected to `css_sanitizer=`.
6. **Streaming held a DB connection for the full LLM duration** — refactored to short-lived sessions.

## A Note on Secrets

All transcripts have been reviewed to remove API keys, tokens, and other sensitive data.
The project uses environment variables (`.env`, gitignored) for all credentials.
