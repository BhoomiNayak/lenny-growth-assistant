# Security & Quality Review

After the core product was working (S0–S4), a dedicated review pass was run over the entire
backend before building further. This was directed as: *"Review for vulnerabilities, logic
bugs, resilience issues, and code quality — focus on XSS, injection, secret leakage, and
resource handling."*

## Findings (7)

| # | Issue | Severity | Resolution |
|---|-------|----------|------------|
| 1 | HTML artifact sanitization bypass | High | Fixed (see below) |
| 2 | DB session held for full streaming duration | High | Fixed — short-lived sessions |
| 3 | Client disconnect loses user message | Medium | Fixed — commit user msg before streaming |
| 4 | SQL interpolation in ingestion index build | Low | Fixed — `assert isinstance` + `int()` cast |
| 5 | No auth / rate limiting | Medium (by design) | Documented as intentional single-tenant demo (PRD A2) |
| 6 | Error message leakage in SSE stream | Medium | Fixed — generic client message, details logged server-side |
| 7 | OpenAI model hardcoded to `gpt-4o` | Low | Fixed — uses `self.model` |

## The Sanitization Saga (Finding #1)

This finding went through **two rounds** of correction, and it's the most instructive:

**Round 1 — content leaked through `strip=True`.** The original sanitizer also re-injected
the original `<style>` block after bleach ran, with only two regex substitutions — an
`@import` exfiltration bypass. First fix: stop re-injecting `<style>`, and (later, when a
unit test caught it) add a regex pass that removes dangerous elements *and their inner
text* because `bleach(strip=True)` was leaving `alert('xss')` as literal text.
See [debugging-highlights.md #4](./debugging-highlights.md).

**Round 2 — `styles=` was silently ignored.** A follow-up review found the CSS allowlist
was configured via `styles=[...]`, which modern bleach does not recognize — so **no CSS
filtering was happening at all**. Corrected to
`css_sanitizer=CSSSanitizer(allowed_css_properties=[...])` (requires `bleach[css]`).
See [debugging-highlights.md #5](./debugging-highlights.md).

The lesson: a filter that *looks* configured but uses the wrong argument name is worse than
no filter, because it gives false confidence. Verified by confirming the module imports
cleanly (proving `tinycss2` is present) and by the sanitization test suite.

## The Streaming DB-Session Refactor (Finding #2)

Original streaming passed the request-scoped `get_db` session into the generator and held
it — and a pooled connection — for the entire LLM response (up to 300s). With a
15-connection pool, ~15 concurrent streams would starve all other DB work.

**Fix:** `_stream_response` now uses short-lived `async_session_factory` sessions per phase
(save user message → committed immediately; load context; pre-retrieve) and performs
retrieval *before* streaming, so no connection is held during generation.
See [debugging-highlights.md #6](./debugging-highlights.md).

## Outcome

All 7 findings resolved or explicitly documented as intentional. The two High-severity
items (sanitization, streaming sessions) received the most attention and follow-up
verification.
