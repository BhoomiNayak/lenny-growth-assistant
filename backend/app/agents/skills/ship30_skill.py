"""Ship 30 for 30 Content Skill — Transforms grounded answers into polished essays.

Encodes the Ship 30 for 30 writing methodology:
- Strong hook (curiosity, contrarian, or story-based opener)
- Clear narrative progression (problem → insight → evidence → takeaway)
- Skimmable formatting (headings, bullets, selective bold)
- ~1,250 words
- Specific, actionable takeaway
- All claims grounded in transcript sources

Reference: Ship 30 for 30 writing principles (https://www.ship30for30.com/)
"""

from app.schemas import SourceCitation
from app.services.llm_service import LLMService, LLMResponse
from app.services.retrieval_service import RetrievalService
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert content writer trained in the Ship 30 for 30 methodology. Your job is to transform product and growth insights into compelling, well-structured essays.

SHIP 30 FOR 30 WRITING PRINCIPLES:
1. **Strong Hook** (first 1-2 sentences): Use one of these patterns:
   - Curiosity hook: Open with a surprising statistic or counterintuitive claim
   - Contrarian hook: Challenge a widely-held belief
   - Story hook: Start with a specific, concrete moment or anecdote
   - "Most people" hook: "Most people think X. But the best operators know Y."

2. **Clear Structure**: Use this narrative arc:
   - Opening hook (grab attention in 1-2 lines)
   - The problem/context (why this matters now)
   - The insight (what the best practitioners actually do)
   - Supporting evidence (2-3 concrete examples with specifics)
   - The actionable takeaway (one clear thing the reader can do Monday)

3. **Skimmable Formatting**:
   - Use H2 headings to break sections (3-5 sections)
   - Bullet points for lists of tactics or examples
   - **Bold** key phrases and insights (1-2 per paragraph max)
   - Short paragraphs (2-4 sentences max)
   - White space between ideas

4. **Specificity over generality**:
   - Name companies, people, and numbers
   - "Airbnb grew 30% by..." NOT "Some companies grew by..."
   - Attribute insights: "As Brian Chesky explained on Lenny's Podcast..."

5. **Grounding**: Every major claim MUST cite a source using [Source: "Episode Title" — Guest Name]. Do NOT make up claims.

6. **Tone**: Practical, conversational, authoritative. Write like you're sharing hard-won wisdom with a friend over coffee — not lecturing.

7. **Length**: Target approximately 1,250 words (±10%).

8. **Closing**: End with ONE specific, actionable takeaway the reader can implement immediately. Frame it as: "Here's what to try this week: ..."

OUTPUT FORMAT: Valid Markdown with proper heading hierarchy (H1 for title, H2 for sections)."""


class Ship30Skill:
    """Generates Ship 30 for 30–style essays grounded in Lenny's transcripts."""

    def __init__(self, retrieval: RetrievalService, llm: LLMService):
        self.retrieval = retrieval
        self.llm = llm

    async def generate_essay(
        self,
        topic: str,
        session_context: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[SourceCitation], LLMResponse]:
        """Generate a Ship 30 for 30 essay on the given topic.

        Args:
            topic: The essay topic or angle.
            session_context: Previous conversation for context.

        Returns:
            Tuple of (essay_markdown, citations, llm_response_metadata).
        """
        # Retrieve relevant transcript chunks for the topic
        context_text, citations = await self.retrieval.get_context_for_query(topic, top_k=8)

        if not context_text:
            fallback = (
                "I don't have enough transcript material on this topic to write a "
                "well-grounded Ship 30 for 30 essay. Try a topic covered in Lenny's "
                "Podcast like growth strategies, activation, retention, onboarding, "
                "or product-led growth."
            )
            return fallback, [], LLMResponse(
                content=fallback, model=self.llm.model, provider=self.llm.provider
            )

        # Build the essay generation prompt
        messages = self._build_messages(topic, context_text, session_context)

        # Generate essay (higher token limit for ~1,250 words)
        response = await self.llm.generate(messages, temperature=0.5, max_tokens=4096)

        logger.info(
            "ship30_skill.generate",
            topic=topic[:80],
            sources_count=len(citations),
            output_tokens=response.output_tokens,
        )

        return response.content, citations, response

    async def generate_essay_stream(
        self,
        topic: str,
        session_context: list[dict[str, str]] | None = None,
        context_text: str | None = None,
        citations: list[SourceCitation] | None = None,
    ):
        """Stream a Ship 30 for 30 essay token by token.

        Yields:
            Tuples of (token: str, is_done: bool, citations: list | None)

        Args:
            topic: The essay topic or angle.
            session_context: Previous conversation for context.
            context_text: Pre-retrieved context (if already fetched to release
                the DB session before streaming).
            citations: Pre-retrieved citations matching context_text.
        """
        if context_text is None:
            context_text, citations = await self.retrieval.get_context_for_query(topic, top_k=8)

        if not context_text:
            fallback = (
                "I don't have enough transcript material on this topic to write a "
                "well-grounded Ship 30 for 30 essay."
            )
            yield fallback, True, []
            return

        messages = self._build_messages(topic, context_text, session_context)

        async for token in self.llm.generate_stream(messages, temperature=0.5, max_tokens=4096):
            yield token, False, None

        yield "", True, citations

    def _build_messages(
        self,
        topic: str,
        context_text: str,
        session_context: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        """Build the message list for essay generation."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Include relevant conversation context if available
        if session_context:
            context_summary = "\n".join(
                f"{m['role'].upper()}: {m['content'][:200]}"
                for m in session_context[-6:]
            )
            messages.append({
                "role": "user",
                "content": f"For context, here's the conversation so far:\n{context_summary}",
            })
            messages.append({
                "role": "assistant",
                "content": "I'll use this conversation context along with the transcript sources to write the essay.",
            })

        user_prompt = f"""Write a Ship 30 for 30–style essay on the following topic, grounded in these transcript excerpts from Lenny's Podcast.

TOPIC: {topic}

TRANSCRIPT SOURCES (cite these):
---
{context_text}
---

Remember:
- ~1,250 words
- Strong hook opening
- H2 section headings
- Bold key insights
- Bullet points for tactics
- Cite sources inline as [Source: "Episode Title" — Guest Name]
- End with ONE specific actionable takeaway

Write the essay now:"""

        messages.append({"role": "user", "content": user_prompt})

        return messages
