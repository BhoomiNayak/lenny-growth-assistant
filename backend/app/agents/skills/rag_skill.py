"""RAG Q&A Skill — Grounded conversational answers with transcript citations.

Retrieves relevant transcript chunks, builds a grounded prompt,
and generates an answer that cites sources inline.
"""

from app.schemas import SourceCitation
from app.services.llm_service import LLMService, LLMResponse
from app.services.retrieval_service import RetrievalService
from app.utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are The Lenny Growth Assistant — an expert AI that answers product management and growth questions using ONLY the provided transcript excerpts from Lenny's Podcast.

RULES:
1. Answer ONLY based on the provided transcript excerpts. Do NOT use outside knowledge.
2. Cite your sources inline using [Source: "Episode Title" — Guest Name].
3. If the excerpts don't contain enough information, say: "I don't have enough information from Lenny's transcripts to answer that confidently."
4. Be specific, actionable, and practical — like the podcast itself.
5. If multiple sources agree, synthesize them. If they disagree, note the different perspectives.
6. Keep answers concise but thorough (2-4 paragraphs for typical questions).
7. Use formatting (bold, bullets) when it aids clarity.

NEVER make up information. NEVER hallucinate sources. If you're unsure, say so."""


class RAGSkill:
    """Grounded Q&A skill that retrieves context and generates cited answers."""

    def __init__(self, retrieval: RetrievalService, llm: LLMService):
        self.retrieval = retrieval
        self.llm = llm

    async def answer(
        self,
        query: str,
        session_context: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[SourceCitation], LLMResponse]:
        """Generate a grounded answer with citations.

        Args:
            query: User's question.
            session_context: Previous messages for follow-up handling.

        Returns:
            Tuple of (answer_text, citations, llm_response_metadata).
        """
        # Retrieve relevant chunks
        context_text, citations = await self.retrieval.get_context_for_query(query)

        if not context_text:
            # No relevant sources found
            no_info_msg = (
                "I don't have enough information from Lenny's transcripts to answer "
                "that confidently. Try asking about topics like product-led growth, "
                "activation, retention, onboarding, or growth team building."
            )
            return no_info_msg, [], LLMResponse(
                content=no_info_msg, model=self.llm.model, provider=self.llm.provider
            )

        # Build messages for the LLM
        messages = self._build_messages(query, context_text, session_context)

        # Generate answer
        response = await self.llm.generate(messages, temperature=0.3, max_tokens=2048)

        logger.info(
            "rag_skill.answer",
            query=query[:80],
            sources_count=len(citations),
            output_tokens=response.output_tokens,
        )

        return response.content, citations, response

    async def answer_stream(
        self,
        query: str,
        session_context: list[dict[str, str]] | None = None,
        context_text: str | None = None,
        citations: list[SourceCitation] | None = None,
    ):
        """Stream a grounded answer token by token.

        Yields:
            Tuples of (token: str, is_done: bool, citations: list | None)

        Args:
            query: User's question.
            session_context: Previous messages for follow-up handling.
            context_text: Pre-retrieved context (if already fetched to release
                the DB session before streaming).
            citations: Pre-retrieved citations matching context_text.
        """
        if context_text is None:
            context_text, citations = await self.retrieval.get_context_for_query(query)

        if not context_text:
            no_info_msg = (
                "I don't have enough information from Lenny's transcripts to answer "
                "that confidently. Try asking about topics like product-led growth, "
                "activation, retention, onboarding, or growth team building."
            )
            yield no_info_msg, True, []
            return

        # Build messages
        messages = self._build_messages(query, context_text, session_context)

        # Stream response
        full_content = ""
        async for token in self.llm.generate_stream(messages, temperature=0.3, max_tokens=2048):
            full_content += token
            yield token, False, None

        # Final yield with citations
        yield "", True, citations

    def _build_messages(
        self,
        query: str,
        context_text: str,
        session_context: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        """Build the message list for the LLM."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Add session context (previous messages for follow-ups)
        if session_context:
            for msg in session_context[-10:]:  # Last 10 messages
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Add the user query with retrieved context
        user_prompt = f"""Based on the following transcript excerpts from Lenny's Podcast, answer the user's question.

TRANSCRIPT EXCERPTS:
---
{context_text}
---

USER QUESTION: {query}"""

        messages.append({"role": "user", "content": user_prompt})

        return messages
