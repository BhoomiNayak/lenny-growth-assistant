# Session S4 — Frontend

**Goal:** A polished React chat UI — session sidebar, streaming message list, artifact
viewer with a sandboxed iframe, model toggle, and source citations.

## Direction Given to the Agent

> "Build the React frontend: session sidebar, chat interface with message list, input with
> auto-resize, artifact viewer with iframe sandbox, model toggle, and source citation
> chips. Follow the design tokens and responsive behavior exactly."

## What Was Built

- `types/index.ts` — TypeScript interfaces mirroring the API contracts
- `api/client.ts` — fetch wrapper + SSE parsing via `ReadableStream`
- `components/` — `SessionSidebar`, `MessageList`, `MessageInput`, `ArtifactViewer`,
  `ModelToggle`, `SourceCitation`
- `App.tsx` — 3-column responsive layout, optimistic user messages, streaming, welcome
  screen, error banner

Key security detail: the artifact viewer renders HTML inside
`<iframe sandbox="">` (empty sandbox = maximum restriction: no scripts, forms, popups,
or same-origin access), on top of server-side sanitization.

## Corrections During the Session

- **CORS origin mismatch.** The frontend runs on port **3010**, but `CORS_ORIGINS` only
  listed 3000/3001. Added `http://localhost:3010` (and `127.0.0.1:3010`) and recreated the
  backend. Preflight then returned 200.
- **`VITE_API_URL`** confirmed pointing to `http://localhost:8001`.

## Verification Gate

- Vite dev server up; page loads (200) with root div.
- **`npx tsc --noEmit` → zero TypeScript errors** (strict mode).
- CORS preflight from `localhost:3010` → 200.

## Outcome

Full UI running at **http://localhost:3010**, type-checked clean, wired to the streaming
API.
