# Manual Test Plan — The Lenny Growth Assistant

This plan covers UI and end-to-end behavior that the automated test suite does not
(streaming rendering, artifact viewer isolation, responsive layout, accessibility).

**Automated tests** (66 passing) cover: API endpoints, retrieval, chunking, agent
routing, persistence, and HTML sanitization. Run them with:

```bash
docker compose exec -T -e TEST_DATABASE_URL="postgresql+asyncpg://lenny:lenny@db:5432/lenny_test" backend python -m pytest
```

---

## Prerequisites

1. `docker compose up -d` — all three services healthy
2. Ollama running with `llama3.1:8b` + `nomic-embed-text` pulled
3. Transcripts ingested: `python scripts/ingest_transcripts.py` (or `--limit 30` for a subset)
4. Open **http://localhost:3010**

---

## 1. Session Management

| # | Step | Expected Result |
|---|------|-----------------|
| 1.1 | Click "New Chat" | A new empty session appears; welcome screen shows |
| 1.2 | Send a message | Session title auto-updates to the first message text |
| 1.3 | Click "New Chat" again, then switch back to the first | Previous conversation reloads with all messages |
| 1.4 | Hover a session in the sidebar, click the trash icon, confirm | Session is removed from the list |
| 1.5 | Delete the active session | Chat area clears; no crash |

---

## 2. Grounded Q&A (RAG)

| # | Step | Expected Result |
|---|------|-----------------|
| 2.1 | Ask "How do you build a high-performing growth team?" | Answer streams in token by token |
| 2.2 | Observe below the answer | Source citation chips appear (guest name) |
| 2.3 | Click a source chip | Excerpt expands; YouTube link opens in new tab |
| 2.4 | Ask a follow-up like "What skills specifically?" | Answer uses prior context (understands "specifically") |
| 2.5 | Ask something off-topic ("What is the capital of France?") | Assistant says it doesn't have enough information from the transcripts |

---

## 3. Ship 30 for 30 Essay

| # | Step | Expected Result |
|---|------|-----------------|
| 3.1 | Ask "Write a Ship 30 for 30 essay on building growth teams" | A long-form essay generates (~1,250 words) |
| 3.2 | Inspect the essay | Has a hook, H2 headings, bullets, bold emphasis, a takeaway |
| 3.3 | Check citations | Claims reference transcript sources |
| 3.4 | Check artifact panel | Essay also appears as a Markdown artifact |

---

## 4. Artifact Generation & Viewer

| # | Step | Expected Result |
|---|------|-----------------|
| 4.1 | Ask "Create an HTML slide deck summarizing our conversation" | Artifact panel opens with rendered HTML |
| 4.2 | Observe the HTML render | Displays inside a sandboxed iframe (styled, not raw code) |
| 4.3 | Check the "sanitized" badge | Present on HTML artifacts |
| 4.4 | Click Copy | Content copied to clipboard (check icon confirms) |
| 4.5 | Click Download | File downloads as `.html` or `.md` |
| 4.6 | Ask "Generate a markdown document of key takeaways" | Markdown artifact renders formatted (not raw) |
| 4.7 | With multiple artifacts, click the tabs | Switches between artifacts |

---

## 5. Artifact Security (Isolation)

| # | Step | Expected Result |
|---|------|-----------------|
| 5.1 | Generate an HTML artifact | Rendered in `<iframe sandbox="">` (inspect element to confirm empty sandbox) |
| 5.2 | Verify no scripts execute | Any `<script>` in generated HTML is stripped server-side (see automated `test_sanitization.py`) |
| 5.3 | Verify no network calls | `@import`, external fetches in artifact CSS are removed |

---

## 6. Model Toggle

| # | Step | Expected Result |
|---|------|-----------------|
| 6.1 | Observe the header pill | Shows "ollama — llama3.1:8b" in green (local) |
| 6.2 | Click the pill | Dropdown lists ollama / anthropic / openai with availability |
| 6.3 | Providers without keys | Shown disabled with reason ("ANTHROPIC_API_KEY not set") |
| 6.4 | If a cloud key is set, switch to it | Pill turns blue; subsequent messages use that provider |

---

## 7. Resilience & Error Handling

| # | Step | Expected Result |
|---|------|-----------------|
| 7.1 | Stop Ollama (`ollama stop` or kill process), send a message | Amber error banner: retryable error, not a crash |
| 7.2 | Click "Retry" in the banner | Message resends |
| 7.3 | Restart Ollama, retry | Works normally |
| 7.4 | Visit `http://localhost:8001/health/ready` while Ollama is down | Shows `status: degraded`, `ollama: error/unavailable` |
| 7.5 | Visit `/health/ready` with everything up | Shows `status: ready` |

---

## 8. Responsive Layout

| # | Step | Expected Result |
|---|------|-----------------|
| 8.1 | Resize to mobile width (< 768px) | Sidebar collapses to a hamburger menu |
| 8.2 | Tap hamburger | Sidebar slides over |
| 8.3 | Artifact panel on mobile | Full-width slide-over |
| 8.4 | Desktop width (> 1024px) | Sidebar + chat + artifact panel visible together |

---

## 9. Accessibility

| # | Step | Expected Result |
|---|------|-----------------|
| 9.1 | Tab through the interface | Focus indicators visible on all interactive elements |
| 9.2 | Cmd/Ctrl+Enter in the input | Sends the message |
| 9.3 | Screen reader (optional) | ARIA labels present on nav, messages (role=log), artifact viewer |
| 9.4 | Check contrast | Text meets WCAG AA (verified in design tokens) |

---

## 10. Observability

| # | Step | Expected Result |
|---|------|-----------------|
| 10.1 | Send any request, check response headers | `X-Correlation-ID` present |
| 10.2 | Check backend logs (`docker compose logs backend`) | `api.request` + `api.response` with matching `correlation_id` and `duration_ms` |
| 10.3 | Trigger an LLM call | `llm.request`, `retrieval.search` logged with timing |

---

## Sign-off

| Area | Pass/Fail | Notes |
|------|-----------|-------|
| Session management | | |
| Grounded Q&A | | |
| Ship 30 for 30 | | |
| Artifact generation | | |
| Artifact security | | |
| Model toggle | | |
| Resilience | | |
| Responsive | | |
| Accessibility | | |
| Observability | | |
