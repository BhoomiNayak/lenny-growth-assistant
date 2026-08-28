"""Artifact Generation Skill — Creates Markdown or HTML/CSS documents.

Generates self-contained artifacts based on conversation context.
HTML artifacts are sanitized server-side before storage.
"""

import bleach
from bleach.css_sanitizer import CSSSanitizer

from app.schemas import SourceCitation
from app.services.llm_service import LLMService, LLMResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Bleach sanitization config
ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "a", "img", "div", "span", "table", "thead",
    "tbody", "tr", "td", "th", "blockquote", "code", "pre", "hr",
    "section", "article", "header", "footer", "nav", "main",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "title", "width", "height"],
    "*": ["class", "style", "id"],
}

ALLOWED_STYLES = [
    "color", "background-color", "background", "font-size", "font-weight",
    "font-family", "text-align", "text-decoration", "line-height",
    "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
    "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
    "border", "border-radius", "width", "height", "max-width",
    "display", "flex-direction", "justify-content", "align-items", "gap",
    "list-style-type", "opacity", "box-shadow",
]

# CSSSanitizer filters inline style attribute values against ALLOWED_STYLES.
# Without this, bleach allows any CSS property value in style attributes.
CSS_SANITIZER = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)

SYSTEM_PROMPT_MARKDOWN = """You are a document generator. Create well-structured Markdown documents based on the conversation context provided.

RULES:
- Output ONLY valid Markdown (no HTML tags inside Markdown)
- Use proper heading hierarchy (H1 title, H2 sections, H3 subsections)
- Include formatting: bold, italic, bullet points, numbered lists, code blocks as appropriate
- Be comprehensive but focused
- If grounded in conversation sources, cite them"""

SYSTEM_PROMPT_HTML = """You are an HTML/CSS artifact generator. Create self-contained, visually polished HTML documents with inline CSS.

RULES:
- Output a COMPLETE HTML document with inline <style> tag
- Use modern CSS (flexbox, grid, custom properties)
- Make it visually appealing with good typography and spacing
- Design must be responsive (works on mobile and desktop)
- Include all styles inline — no external CSS or JavaScript files
- Do NOT include <script> tags (they will be removed for security)
- Do NOT include <form>, <input>, or <iframe> tags
- Use a clean, professional color palette
- The document should be self-contained and render beautifully on its own"""


class ArtifactSkill:
    """Generates Markdown or HTML/CSS artifacts from conversation context."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def generate(
        self,
        prompt: str,
        artifact_type: str = "markdown",
        session_context: list[dict[str, str]] | None = None,
    ) -> tuple[str, str, bool]:
        """Generate an artifact based on the prompt and conversation.

        Args:
            prompt: User's request for what to generate.
            artifact_type: "markdown" or "html".
            session_context: Previous conversation messages.

        Returns:
            Tuple of (content, title, was_sanitized).
        """
        messages = self._build_messages(prompt, artifact_type, session_context)

        response = await self.llm.generate(messages, temperature=0.4, max_tokens=4096)
        content = response.content
        sanitized = False

        # Extract title from generated content
        title = self._extract_title(content, artifact_type, prompt)

        # Sanitize HTML artifacts
        if artifact_type == "html":
            content, sanitized = self._sanitize_html(content)

        logger.info(
            "artifact_skill.generate",
            type=artifact_type,
            title=title[:50],
            sanitized=sanitized,
            output_tokens=response.output_tokens,
        )

        return content, title, sanitized

    def _build_messages(
        self,
        prompt: str,
        artifact_type: str,
        session_context: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        """Build messages for artifact generation."""
        system = SYSTEM_PROMPT_HTML if artifact_type == "html" else SYSTEM_PROMPT_MARKDOWN

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
        ]

        # Add conversation context
        if session_context:
            context_str = "\n\n".join(
                f"**{m['role'].upper()}**: {m['content'][:500]}"
                for m in session_context[-8:]
            )
            messages.append({
                "role": "user",
                "content": f"Here is the conversation context to base the artifact on:\n\n{context_str}",
            })
            messages.append({
                "role": "assistant",
                "content": f"I'll create a {artifact_type} artifact based on this conversation.",
            })

        messages.append({
            "role": "user",
            "content": f"Generate a {artifact_type} artifact: {prompt}",
        })

        return messages

    def _extract_title(self, content: str, artifact_type: str, fallback: str) -> str:
        """Extract a title from the generated content."""
        lines = content.strip().split("\n")

        if artifact_type == "markdown":
            for line in lines[:5]:
                if line.startswith("# "):
                    return line[2:].strip()[:100]
        elif artifact_type == "html":
            import re
            title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE)
            if title_match:
                return title_match.group(1).strip()[:100]
            h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.IGNORECASE)
            if h1_match:
                return h1_match.group(1).strip()[:100]

        # Fallback: use first 50 chars of prompt
        return fallback[:50].strip() if fallback else "Untitled Artifact"

    def _sanitize_html(self, html: str) -> tuple[str, bool]:
        """Sanitize HTML content for safe rendering.

        Two-stage defense:
        1. Remove the *entire content* of dangerous elements (script, style,
           iframe, object, embed, form) — bleach's strip=True only removes the
           tags but keeps their inner text, so we pre-strip these blocks. This
           also prevents CSS-based exfiltration via @import, -moz-binding, etc.
        2. Run bleach with an allowlist of tags/attributes to strip everything
           else unsafe (event handlers, javascript: URLs, disallowed tags).

        Returns (sanitized_html, was_modified).
        """
        import re

        original = html

        # Stage 1: remove dangerous elements INCLUDING their content
        dangerous_elements = ["script", "style", "iframe", "object", "embed", "form", "noscript"]
        for tag in dangerous_elements:
            html = re.sub(
                rf"<{tag}\b[^>]*>.*?</{tag}>",
                "",
                html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            # Also remove any self-closing/unclosed variants
            html = re.sub(rf"<{tag}\b[^>]*/?>", "", html, flags=re.IGNORECASE)

        # Stage 2: bleach allowlist for everything else
        sanitized = bleach.clean(
             html,
             tags=ALLOWED_TAGS,
             attributes=ALLOWED_ATTRIBUTES,
             css_sanitizer=CSS_SANITIZER,
             strip=True,
         )

        was_modified = sanitized != original
        return sanitized, was_modified
