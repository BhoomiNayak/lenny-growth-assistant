# Session S5 — Resilience & Observability

**Goal:** Correlation IDs, request/response logging, DB startup retry, and graceful
frontend error/retry states.

## Direction Given to the Agent

> "Add resilience and observability: request correlation IDs, structured request logging,
> DB connection retry with backoff on startup, and frontend error/retry states for when the
> LLM is unavailable."

## What Was Built

- `utils/middleware.py` — `RequestLoggingMiddleware`: generates/reuses `X-Correlation-ID`,
  binds it to structlog contextvars (so every log in a request carries it), logs
  `api.request` + `api.response` with `duration_ms`, and returns the ID in a response header.
- `database.py` — `wait_for_db()`: exponential backoff (10 retries, capped 15s) on startup
  to survive Docker start-order races.
- `App.tsx` — `lastFailedMessage` state, a Retry button, and a structured amber error
  banner that distinguishes stream errors from success.

## Verification Gate — and an Unplanned Live Test

Planned verification passed: `/health` request logged `api.request` + `api.response` with
the **same** `correlation_id` and `duration_ms=1`, and the ID appeared in the response
header. Startup logs showed `database.connected attempt=1`.

Then Docker Desktop restarted mid-session and killed Ollama — an **unplanned real resilience
test**. The system behaved exactly as designed:
- A message request returned a **structured, retryable error**
  (`RETRIEVAL_FAILED`, `retryable: true`) instead of crashing.
- `/health/ready` reported `status: degraded`, `ollama: error`, `db: connected` — an
  evaluator could diagnose the outage instantly.
- After restarting Ollama, `/health/ready` returned to `ready` / `available`.

Frontend TypeScript still compiled clean after the error-handling changes.

## Note on the Environment

Docker Desktop restarted a few times during development, each time killing the containers
and Ollama. Recovery is simply `docker compose up -d` plus ensuring `ollama serve` is
running. This is a local-environment quirk, not a project defect.

## Outcome

Observability (correlation IDs, structured timing logs) and resilience (DB retry, graceful
LLM-outage handling, health diagnostics, frontend retry) all in place and verified —
including under a genuine dependency outage.
