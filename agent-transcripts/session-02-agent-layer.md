# Session S2 — Agent Layer & Skills

**Goal:** An LLM provider factory plus three distinct skills (RAG Q&A, Ship 30 for 30
essay, Artifact generator) behind a skill router.

## Direction Given to the Agent

> "Set up the agent layer with three skills: RAG Q&A, Ship 30 for 30 writer, and Artifact
> generator. Include the skill router, model toggle factory, and Ollama fallback behavior."

Emphasis: the Ship 30 for 30 skill must **encode the actual writing methodology** (hook
patterns, narrative arc, skimmable formatting, ~1,250 words, grounded citations) in the
system prompt — not rely on a vague "write well" instruction.

## What Was Built

- `services/llm_service.py` — unified `LLMService` with `generate()` and
  `generate_stream()`, supporting Ollama, Anthropic, and OpenAI. Structured errors on
  connect failure / timeout / missing key.
- `agents/skills/rag_skill.py` — retrieves top-k chunks, builds grounded prompt, cites
  sources inline; returns "not enough information" when retrieval is empty.
- `agents/skills/ship30_skill.py` — full Ship 30 for 30 methodology encoded in the system
  prompt; retrieves broader context (top-8).
- `agents/skills/artifact_skill.py` — Markdown/HTML generation with server-side HTML
  sanitization.
- `agents/base.py` — `SkillRouter` (keyword routing) + `AgentOrchestrator` (dispatch +
  `AgentResponse`).

## Failed Attempts & Corrections

### Ollama 500 on the first RAG prompt
Short prompts worked; the first real RAG prompt (system + 5 chunks) returned HTTP 500.
Cause: `options.num_predict` with a large prompt + too-small default context. **Fix:**
removed `num_predict`, added `num_ctx: 8192`, raised timeout to 300s, and added explicit
non-200 handling. See [debugging-highlights.md #3](./debugging-highlights.md).

### Skill router misses
Two routing test cases failed initially — "Create an HTML slide deck" and "Generate a
markdown document" routed to `rag` instead of `artifact`. **Fix:** added `slide deck`,
`presentation`, and `markdown document` to the artifact keyword list.

## Verification Gate

- Skill router: 6/6 routing cases correct after the keyword fixes.
- RAG skill (live Ollama): "How do you build a high-performing growth team?" returned a
  grounded answer citing the Adam Fishman episode, with bold/bullet formatting. Latency
  ~50s (expected for 8B-on-CPU).

## Outcome

All three skills functional; router verified. Latency on local model noted as a known
trade-off (documented in the PRD and addressed by the cloud toggle + streaming).
