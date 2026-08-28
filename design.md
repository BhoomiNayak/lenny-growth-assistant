# Design Document
# The Lenny Growth Assistant

**Version:** 1.0  
**Date:** 2026-08-26  
**Author:** [Your Name]

---

## 1. Design Principles

1. **Clarity over cleverness** — Every element has a clear purpose. No mystery meat navigation.
2. **Grounding is visible** — Sources are first-class citizens, not afterthoughts.
3. **Progressive disclosure** — Show what's needed, hide what isn't. Artifacts appear when relevant.
4. **Respect the model** — The model toggle is visible and honest about limitations.
5. **Accessible by default** — Keyboard-navigable, screen-reader friendly, high contrast.

---

## 2. Information Architecture

```
App
├── Header
│   ├── Logo + Title
│   ├── Model Toggle (pill/badge)
│   └── Settings (future)
│
├── Main Layout (3-column on desktop)
│   ├── Sidebar (20%) — Sessions
│   │   ├── New Chat Button
│   │   └── Session List (scrollable)
│   │       ├── Session Item (title, timestamp, active state)
│   │       └── Delete action (hover)
│   │
│   ├── Chat Area (50-60%) — Primary
│   │   ├── Welcome State (empty chat)
│   │   ├── Message List (scrollable)
│   │   │   ├── User Message (right-aligned, distinct background)
│   │   │   └── Assistant Message (left-aligned)
│   │   │       ├── Content (Markdown rendered)
│   │   │       ├── Source Citations (chips below message)
│   │   │       └── Actions (copy, regenerate — future)
│   │   ├── Typing Indicator (streaming)
│   │   └── Input Area (fixed bottom)
│   │       ├── Textarea (auto-resize)
│   │       ├── Send Button
│   │       └── Shortcut hint (Cmd+Enter)
│   │
│   └── Artifact Panel (25-30%) — Collapsible
│       ├── Panel Header (title + close)
│       ├── Artifact List (tabs or accordion)
│       └── Artifact Viewer
│           ├── Markdown Renderer (safe)
│           └── HTML Renderer (sandboxed iframe)
│
└── Footer (minimal)
    └── Status bar (connection, model info)
```

---

## 3. Key Interaction States

### 3.1 Empty State

```
┌─────────────────────────────────────────────────────────────┐
│  Lenny Growth Assistant              [Ollama ▼]              │
├──────────┬──────────────────────────────┬───────────────────┤
│          │                              │                   │
│  + New   │      🤖 Welcome              │                   │
│  Chat    │                              │   Artifacts       │
│          │  Ask me anything about       │   ─────────────   │
│  ─────   │  product and growth.         │                   │
│          │                              │   No artifacts    │
│  Chat 1  │  I can:                      │   yet.            │
│  Chat 2  │  • Answer questions from     │                   │
│  Chat 3  │    Lenny's transcripts       │                   │
│          │  • Write Ship 30for30 essays │                   │
│          │  • Generate artifacts        │                   │
│          │                              │                   │
│          │  [Try: "How did Figma        │                   │
│          │   grow their user base?"]     │                   │
│          │                              │                   │
│          │                              │                   │
│          │  ┌────────────────────────┐ │                   │
│          │  │ Ask anything...        │ │                   │
│          │  │                        │ │                   │
│          │  └────────────────────────┘ │                   │
│          │                              │                   │
└──────────┴──────────────────────────────┴───────────────────┘
```

### 3.2 Active Chat State

```
┌─────────────────────────────────────────────────────────────┐
│  Lenny Growth Assistant         [Ollama — llama3.1 ▼]      │
├──────────┬──────────────────────────────┬───────────────────┤
│          │  User: How did Airbnb...     │                   │
│  + New   │                              │   📄 Retention    │
│  Chat    │  🤖 Assistant:               │   Essay           │
│          │  Airbnb focused on...        │   ─────────────   │
│  ─────   │                              │   [Preview]       │
│          │  [Source: Brian Chesky]          │                   │
│  Chat 1  │  [Source: Casey Winters]         │   📊 HTML Deck    │
│  Chat 2  │                              │   ─────────────   │
│  Chat 3  │  User: What about onboarding?│   [Preview]       │
│  (active)│                              │                   │
│          │  🤖 Assistant:               │                   │
│          │  For onboarding, they...     │                   │
│          │                              │                   │
│          │  [Source: Brian Chesky]       │                   │
│          │                              │                   │
│          │  ┌────────────────────────┐ │                   │
│          │  │ What specific tactic...  │ │                   │
│          │  │                        │ │                   │
│          │  └────────────────────────┘ │                   │
│          │                              │                   │
└──────────┴──────────────────────────────┴───────────────────┘
```

### 3.3 Streaming State

```
┌─────────────────────────────────────────────────────────────┐
│  Lenny Growth Assistant         [Ollama — llama3.1 ▼]      │
├──────────┬──────────────────────────────┬───────────────────┤
│          │  User: How did Airbnb...     │                   │
│          │                              │                   │
│          │  🤖 Assistant:               │                   │
│          │  Airbnb focused on the       │                   │
│          │  "aha moment" of seeing      │                   │
│          │  your first booking...       │                   │
│          │  ▋ (cursor blinking)         │                   │
│          │                              │                   │
│          │  Retrieving sources...       │                   │
│          │  [░░░░░░░░] (progress)       │                   │
│          │                              │                   │
│          │  ┌────────────────────────┐  │                   │
│          │  │                        │  │                   │
│          │  │  (disabled while streaming) │                │
│          │  └────────────────────────┘  │                   │
│          │                              │                   │
└──────────┴──────────────────────────────┴───────────────────┘
```

### 3.4 Model Toggle Dropdown

```
┌─────────────────────────────────────────────────────────────┐
│  Lenny Growth Assistant         [Ollama — llama3.1 ▼]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    ┌─────────────────────┐                  │
│                    │  🖥️ Local Models    │                  │
│                    │  ─────────────────  │                  │
│                    │  ● llama3.1:8b      │                  │
│                    │  ○ qwen2.5:7b       │                  │
│                    │                     │                  │
│                    │  ☁️ Cloud Models    │                  │
│                    │  ─────────────────  │                  │
│                    │  ○ Claude 3.5 Sonnet│                  │
│                    │  ○ GPT-4o           │                  │
│                    │                     │                  │
│                    │  ⚠️ Ollama not      │                  │
│                    │     running         │                  │
│                    └─────────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 SessionSidebar

**Props:**
```typescript
interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
}
```

**Behavior:**
- Collapsible on mobile (hamburger menu)
- Sessions sorted by `updated_at` desc
- Active session highlighted with left border accent
- Hover shows delete button (with confirmation)
- New Chat button always visible at top

### 4.2 MessageList

**Props:**
```typescript
interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
}
```

**Behavior:**
- Auto-scroll to bottom on new messages
- Smooth scroll animation
- User messages: right-aligned, primary color background
- Assistant messages: left-aligned, neutral background
- Markdown rendering for assistant content
- Source citations as clickable chips below assistant messages
- Clicking source chip shows excerpt tooltip

### 4.3 MessageInput

**Props:**
```typescript
interface MessageInputProps {
  onSend: (content: string) => void;
  disabled: boolean;
  placeholder?: string;
}
```

**Behavior:**
- Auto-resize textarea (max 5 rows)
- Cmd/Ctrl + Enter to send
- Enter for new line
- Disabled state during streaming
- Send button disabled when empty

### 4.4 ArtifactViewer

**Props:**
```typescript
interface ArtifactViewerProps {
  artifacts: Artifact[];
  activeArtifactId?: string;
  onSelectArtifact: (id: string) => void;
  onClose: () => void;
}
```

**Behavior:**
- Collapsible panel (slide in from right)
- Tab/accordion list of artifacts
- Markdown: rendered with safe parser (no raw HTML)
- HTML: rendered in sandboxed iframe
- Copy button for raw content
- Download button (.md or .html)
- Full-screen toggle

### 4.5 ModelToggle

**Props:**
```typescript
interface ModelToggleProps {
  currentProvider: 'ollama' | 'anthropic' | 'openai';
  currentModel: string;
  availableProviders: ProviderConfig[];
  onSwitch: (provider: string, model: string) => void;
}
```

**Behavior:**
- Pill/badge in header
- Color coding: green (local), blue (cloud)
- Dropdown on click
- Shows provider status (available/unavailable)
- Switching takes effect for next message

### 4.6 SourceCitation

**Props:**
```typescript
interface Source {
  episode_id: string;
  guest: string;
  episode_title: string;
  youtube_url?: string;
  publish_date?: string;
  excerpt: string;
}

interface SourceCitationProps {
  sources: Source[];
}
```

**Behavior:**
- Horizontal row of chips
- Each chip: guest name + episode title (truncated)
- Hover: tooltip with excerpt
- Click: expand to show full excerpt + YouTube link (opens in new tab)
- Max 3 visible, "+2 more" expander

---

## 5. Responsive Behavior

### Breakpoints

| Breakpoint | Layout | Sidebar | Artifact Panel |
|------------|--------|---------|----------------|
| < 768px (mobile) | Single column | Hidden, slide-over | Hidden, slide-over |
| 768-1024px (tablet) | Two column | Visible, 240px | Hidden, slide-over |
| > 1024px (desktop) | Three column | Visible, 280px | Visible, 320px |

### Mobile Behavior

```
┌─────────────────────────────┐
│  ≡  Lenny Growth Assistant  │
├─────────────────────────────┤
│                             │
│  (Chat takes full width)    │
│                             │
│                             │
│                             │
│                             │
│                             │
│  ┌────────────────────────┐ │
│  │ Ask anything...        │ │
│  └────────────────────────┘ │
│                             │
└─────────────────────────────┘
```

- Sidebar: slide-over from left
- Artifact panel: slide-over from right
- Model toggle: compact (icon only)
- Input: full-width, fixed bottom

---

## 6. Accessibility Considerations

### 6.1 Keyboard Navigation

| Key | Action |
|-----|--------|
| Tab | Navigate between interactive elements |
| Shift+Tab | Reverse navigation |
| Enter | Activate button, send message (when input focused) |
| Cmd+Enter | Send message (when textarea focused) |
| Escape | Close sidebar, close artifact panel, cancel streaming |
| Arrow Up | Navigate session list |

### 6.2 ARIA Labels

```html
<!-- Session sidebar -->
<nav aria-label="Chat sessions">
  <button aria-label="Start new chat">+ New Chat</button>
  <ul role="list">
    <li aria-current="page">Chat 1</li>
  </ul>
</nav>

<!-- Message list -->
<main aria-label="Chat messages" role="log" aria-live="polite">
  <article aria-label="Assistant message">
    <div>Content...</div>
    <footer aria-label="Sources">
      <button aria-label="Source: Episode 142, 23:15">Ep.142</button>
    </footer>
  </article>
</main>

<!-- Artifact viewer -->
<aside aria-label="Artifact viewer">
    <iframe title="Artifact preview" sandbox=""></iframe>
</aside>
```

### 6.3 Focus Management

- Focus trap in modals/slide-overs
- Focus returns to trigger element on close
- Visible focus indicators (2px outline, offset 2px)
- Skip link to main content

### 6.4 Color & Contrast

| Element | Background | Text | Contrast Ratio |
|---------|-----------|------|----------------|
| Primary button | `#2563eb` | `#ffffff` | 4.6:1 |
| User message | `#dbeafe` | `#1e3a5f` | 7.2:1 |
| Assistant message | `#f8fafc` | `#1e293b` | 12.1:1 |
| Source chip | `#f1f5f9` | `#475569` | 5.8:1 |
| Error | `#fef2f2` | `#991b1b` | 7.5:1 |

---

## 7. Design Tokens

### Colors

```css
:root {
  /* Primary */
  --color-primary-50: #eff6ff;
  --color-primary-100: #dbeafe;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;
  --color-primary-700: #1d4ed8;

  /* Neutral */
  --color-neutral-50: #f8fafc;
  --color-neutral-100: #f1f5f9;
  --color-neutral-200: #e2e8f0;
  --color-neutral-300: #cbd5e1;
  --color-neutral-500: #64748b;
  --color-neutral-600: #475569;
  --color-neutral-700: #334155;
  --color-neutral-900: #0f172a;

  /* Semantic */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;

  /* Model indicators */
  --color-local: #22c55e;    /* Green */
  --color-cloud: #3b82f6;   /* Blue */
}
```

### Typography

```css
:root {
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
}
```

### Spacing

```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
}
```

### Shadows & Borders

```css
:root {
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);

  --radius-sm: 0.375rem;  /* 6px */
  --radius-md: 0.5rem;    /* 8px */
  --radius-lg: 0.75rem;   /* 12px */
  --radius-xl: 1rem;      /* 16px */

  --border-default: 1px solid var(--color-neutral-200);
}
```

---

## 8. Animation & Motion

### Principles
- Subtle, purposeful motion
- Respect `prefers-reduced-motion`
- Never block interaction with animation

### Defined Animations

| Animation | Duration | Easing | Trigger |
|-----------|----------|--------|---------|
| Message appear | 200ms | ease-out | New message |
| Sidebar slide | 300ms | cubic-bezier(0.4, 0, 0.2, 1) | Toggle |
| Artifact panel slide | 300ms | cubic-bezier(0.4, 0, 0.2, 1) | Toggle |
| Typing dots | 1.4s | ease-in-out | Streaming |
| Source chip hover | 150ms | ease | Hover |
| Toast notification | 300ms in, 200ms out | ease | Error/success |

### Streaming Indicator

```
●○○  →  ○●○  →  ○○●  →  ●○○  (loop)
```

Three dots, each 200ms apart, pulsing opacity.

---

## 9. Error States

### 9.1 LLM Unavailable

```
┌─────────────────────────────────────────┐
│  ⚠️  Local model (Ollama) is not        │
│      running. Switch to cloud model?    │
│                                         │
│      [Switch to Claude 3.5]  [Retry]   │
└─────────────────────────────────────────┘
```

### 9.2 Empty Retrieval

```
┌─────────────────────────────────────────┐
│  🤔 I don't have enough information     │
│     to answer that confidently.         │
│                                         │
│     Try asking about:                   │
│     • Product-led growth                │
│     • Activation strategies             │
│     • Retention metrics                 │
└─────────────────────────────────────────┘
```

### 9.3 Network Error

```
┌─────────────────────────────────────────┐
│  ❌  Failed to send message            │
│      Check your connection and retry.    │
│                                         │
│                    [Retry]              │
└─────────────────────────────────────────┘
```

---

## 10. Ship 30for30 Essay Rendering

The essay artifact uses a specific Markdown structure:

```markdown
# [Strong Hook Title]

**Opening hook** — one sentence that grabs attention.

## The Problem

Context and why it matters.

## What [Company] Did

- **Bold key insight**
- Supporting detail with [Source: Episode X]
- Another insight

## The Results

Specific outcomes.

## Your Takeaway

One actionable thing to try.
```

**Rendering rules:**
- H1: 24px, bold, primary color
- H2: 20px, semibold, neutral-700
- Bold text: primary-600
- Bullet points: relaxed line-height
- Source citations: small, muted, italic
- Max width: 680px for readability

---

*Next step: Implement with Kiro in Session S4.*
