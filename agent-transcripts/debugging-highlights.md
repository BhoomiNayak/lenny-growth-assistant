# Debugging Highlights

The six most instructive debugging episodes from the build, each showing the symptom,
the failed/incorrect assumptions, the root cause, and the fix. These are the moments
where directing the agent — and verifying its output rather than trusting it — mattered
most.

---

## 1. Retrieval returned 0 results despite 152 stored embeddings (the IVFFlat trap)

**Symptom.** After ingesting 3 episodes (152 chunks), a vector search for
"How to build a growth team?" returned **zero** results — even with no similarity
threshold and a plain `LIMIT 5`.

**Diagnostics run (in order).**
- `SELECT count(*) FROM transcript_chunks` → 152 rows, all with embeddings.
- `vector_dims(embedding)` → 768 (matches `nomic-embed-text`). Dimensions fine.
- Self-similarity `1 - (embedding <=> embedding)` → `1.0`. The distance operator works.
- Single-row distance against a fresh query embedding → `0.40`. Also fine.
- `LIMIT 3` **without** `ORDER BY` → 3 rows. But `ORDER BY embedding <=> $1 LIMIT 3` → **0 rows**.

That last contradiction was the tell: an ordered index scan returned nothing while a
sequential scan returned rows.

**Wrong hypotheses considered and ruled out.** Threshold too high (removed it — still 0),
embeddings not normalized (self-similarity was 1.0), model mismatch (same model for
ingest and query), wrong dimension (both 768).

**Root cause.** The `IVFFlat` index was created in the Alembic migration — i.e. **on an
empty table**. IVFFlat computes its cluster centroids at index-creation time. Built with
zero rows, the centroids are degenerate, so any query that uses the index (`ORDER BY
embedding <=> ...`) probes empty lists and returns nothing.

**Fix.**
- Removed `CREATE INDEX ... ivfflat` from migration `001` (with an explanatory comment).
- The ingestion script now builds the index **after** data is loaded, sized with
  `lists = sqrt(row_count)`.
- Until the index exists, exact sequential-scan cosine search is used — 100% accurate and
  fast at this corpus size.

**Verification.** Dropping the index made the same query return 5 relevant results
(top match: the Adam Fishman "high-performing growth team" episode at ~0.69 similarity).

---

## 2. asyncpg cannot bind `:param::vector`

**Symptom.** The ingestion INSERT and the retrieval query both failed with
`asyncpg ... PostgresSyntaxError: syntax error at or near ":"`.

**Root cause.** The SQL used pgvector's `::vector` cast on a bound parameter
(`:embedding::vector`). asyncpg's parameter substitution collides with the `::` cast
syntax when the parameter is passed as a driver-bound value.

**Fix.** Switched to the functional cast form `CAST(:embedding AS vector)` in the
retrieval service, and in the ingestion script used `cast(:embedding as vector)` inside a
`text()` statement with the embedding formatted as a pgvector string literal
(`"[0.1,0.2,...]"`).

**Verification.** Ingestion stored 152 chunks with no errors; retrieval returned ranked results.

---

## 3. Ollama returned HTTP 500 on the first real RAG prompt

**Symptom.** Short prompts to `/api/chat` worked, but the first RAG prompt (system +
5 retrieved chunks, ~2000+ tokens) returned `500 Internal Server Error`.

**Root cause.** The request set `options.num_predict` alongside a large prompt; the
combination tripped an Ollama error. The default context window was also too small for
the retrieved context.

**Fix.** Removed `num_predict`, added `num_ctx: 8192`, and raised the client timeout to
300s to accommodate slower local generation. Also added explicit non-200 handling so a
future Ollama error surfaces as a structured `LLMUnavailableError` instead of an
unhandled `raise_for_status()`.

**Verification.** The RAG query then returned a grounded, well-formatted answer citing the
correct episode.

---

## 4. Bleach stripped `<script>` tags but kept the payload text

**Symptom.** A sanitization unit test failed:
`assert 'alert' not in cleaned` — the output was `<div>Safe</div>alert('xss')`.

**Root cause.** `bleach.clean(..., strip=True)` removes disallowed **tags** but preserves
their **text content**. So `<script>alert('xss')</script>` became the literal text
`alert('xss')`.

**Fix.** Added a first-stage regex pass that removes dangerous elements **and their entire
content** (`script`, `style`, `iframe`, `object`, `embed`, `form`, `noscript`) before
handing off to bleach's allowlist. (This was later refined further — see #5.)

**Verification.** All 14 sanitization tests pass, including `@import` CSS-exfiltration and
`<script>` payload cases.

---

## 5. Bleach `styles=` was the wrong parameter name

**Symptom.** During final review, inline `style` attributes were passing through
unfiltered even though an allowlist of CSS properties had been configured.

**Root cause.** The code passed `styles=[...]` to `bleach.clean()`. In modern bleach, CSS
filtering is configured via a `css_sanitizer=CSSSanitizer(...)` object — `styles=` is not
a recognized argument, so it was **silently ignored** and no CSS filtering occurred.

**Fix.** Replaced `styles=` with a proper `css_sanitizer=CSSSanitizer(allowed_css_properties=[...])`.
This requires the `bleach[css]` extra (`tinycss2`).

**Verification.** The artifact skill imports cleanly in the container (confirming
`tinycss2` is present) and inline styles are now filtered against the allowlist.

**Lesson.** A silently-ignored keyword argument is a dangerous class of bug — the code
*looks* like it sanitizes CSS but does nothing. Worth checking library signatures when a
filter "isn't taking effect."

---

## 6. Streaming held a database connection for the entire LLM call

**Symptom.** Flagged in the security/quality review: the SSE streaming endpoint kept its
dependency-injected DB session (and a pooled connection) open for the full duration of
the LLM response — up to the 300s timeout. With a 15-connection pool, ~15 concurrent
streams would starve all other DB operations.

**Root cause.** The streaming generator was passed the request-scoped `get_db` session and
did all its work (save user message, load context, save assistant message) within that
single long-lived session that stayed open during token generation.

**Fix.** Refactored `_stream_response` to use short-lived sessions from
`async_session_factory` for each discrete phase — save the user message (committed
immediately so a client disconnect can't lose it), load context, and pre-retrieve — so no
DB connection is held during the LLM generation itself. Retrieval was moved to *before*
streaming begins.

**Verification.** Streaming still works end-to-end; the DB connection is released during
the long LLM phase.

---

## Meta-lesson

Every one of these was caught by **verifying behavior, not trusting output**: running the
query, reading the logs, writing a failing test, or reviewing the diff. The agent produced
working-looking code in each case; the bugs only surfaced under real execution and review.
