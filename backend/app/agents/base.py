"""Agent Orchestrator — Routes user messages to the appropriate skill.

Determines intent from the message content and dispatches to:
- RAGSkill: Default for Q&A
- Ship30Skill: Essay generation
- ArtifactSkill: Document/HTML generation
"""

from dataclasses import dataclass
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.skills.rag_skill import RAGSkill
from app.agents.skills.ship30_skill import Ship30Skill
from app.agents.skills.artifact_skill import ArtifactSkill
from app.schemas import SourceCitation
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentResponse:
    """Complete response from the agent orchestrator."""

    content: str
    sources: list[SourceCitation]
    skill_used: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    artifact_content: str | None = None
    artifact_type: str | None = None
    artifact_title: str | None = None
    artifact_sanitized: bool = False


class SkillRouter:
    """Determines which skill to invoke based on message content."""

    # Keywords that trigger Ship 30 for 30 skill
    SHIP30_KEYWORDS = [
        "ship 30 for 30", "ship 30for30", "ship30for30",
        "write an essay", "write a blog post", "write an article",
        "turn this into an essay", "turn that into an essay",
        "write a piece", "long-form", "longform",
    ]

    # Keywords that trigger Artifact skill
    ARTIFACT_KEYWORDS = [
        "create html", "generate html", "make html",
        "create a slide", "generate a slide", "make a slide",
        "slide deck", "presentation",
        "create a document", "generate a document", "make a document",
        "create an artifact", "generate an artifact",
        "create markdown", "generate markdown", "markdown document",
        "build a table", "create a chart", "make a presentation",
        "export as", "download as",
    ]

    def route(self, message: str, session_context: list[dict] | None = None) -> str:
        """Determine which skill to use.

        Returns:
            Skill name: "rag", "ship30", or "artifact"
        """
        msg_lower = message.lower()

        # Check for artifact generation intent
        if any(kw in msg_lower for kw in self.ARTIFACT_KEYWORDS):
            return "artifact"

        # Check for Ship 30 for 30 intent
        if any(kw in msg_lower for kw in self.SHIP30_KEYWORDS):
            return "ship30"

        # Default: RAG Q&A
        return "rag"

    def detect_artifact_type(self, message: str) -> str:
        """Detect whether the user wants markdown or html."""
        msg_lower = message.lower()
        html_indicators = ["html", "slide", "presentation", "chart", "visual", "styled"]
        if any(ind in msg_lower for ind in html_indicators):
            return "html"
        return "markdown"


class AgentOrchestrator:
    """Main agent that routes messages to skills and manages responses."""

    def __init__(self, db: AsyncSession | None = None, provider: str | None = None, model: str | None = None):
        self.db = db
        self.llm = LLMService(provider=provider, model=model)
        self.retrieval = RetrievalService(db)
        self.router = SkillRouter()

        # Initialize skills
        self.rag_skill = RAGSkill(self.retrieval, self.llm)
        self.ship30_skill = Ship30Skill(self.retrieval, self.llm)
        self.artifact_skill = ArtifactSkill(self.llm)

    async def process_message(
        self,
        message: str,
        session_context: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Process a user message and return the complete response.

        Args:
            message: User's message content.
            session_context: Previous messages in the session.

        Returns:
            AgentResponse with content, sources, and metadata.
        """
        # Route to appropriate skill
        skill_name = self.router.route(message, session_context)

        logger.info(
            "agent.routing",
            skill=skill_name,
            message_preview=message[:60],
        )

        if skill_name == "ship30":
            return await self._handle_ship30(message, session_context)
        elif skill_name == "artifact":
            return await self._handle_artifact(message, session_context)
        else:
            return await self._handle_rag(message, session_context)

    async def process_message_stream(
        self,
        message: str,
        session_context: list[dict[str, str]] | None = None,
        context_text: str | None = None,
        citations: list[SourceCitation] | None = None,
    ) -> AsyncGenerator[tuple[str, bool, list[SourceCitation] | None, str, dict | None], None]:
        """Stream a response token by token.

        Yields:
            Tuples of (token, is_done, citations_if_done, skill_used, artifact_data)
            where artifact_data is a dict with keys: content, type, title, sanitized
            or None if no artifact was generated.

        Args:
            message: User's message content.
            session_context: Previous messages in the session.
            context_text: Pre-retrieved context (if already fetched to release
                the DB session before streaming). When provided, retrieval is
                skipped in the skills and the DB connection can be closed.
            citations: Pre-retrieved citations matching context_text.
        """
        skill_name = self.router.route(message, session_context)

        logger.info("agent.routing_stream", skill=skill_name, message_preview=message[:60])

        if skill_name == "rag":
            async for token, done, done_citations in self.rag_skill.answer_stream(
                message, session_context, context_text, citations
            ):
                yield token, done, done_citations, "rag", None
        elif skill_name == "ship30":
            full_content = ""
            final_citations: list[SourceCitation] = []
            async for token, done, done_citations in self.ship30_skill.generate_essay_stream(
                message, session_context, context_text, citations
            ):
                if done:
                    final_citations = done_citations or []
                else:
                    full_content += token
                    yield token, False, None, "ship30", None
            topic = self._extract_topic(message)
            yield "", True, final_citations, "ship30", {
                "content": full_content,
                "type": "markdown",
                "title": f"Ship 30 Essay: {topic[:50]}",
                "sanitized": False,
            }
        else:
            # Artifact generation is not streamed (needs post-processing/sanitization)
            response = await self._handle_artifact(message, session_context)
            yield response.content, True, response.sources, "artifact", {
                "content": response.artifact_content,
                "type": response.artifact_type,
                "title": response.artifact_title,
                "sanitized": response.artifact_sanitized,
            }

    async def _handle_rag(
        self, message: str, session_context: list[dict] | None
    ) -> AgentResponse:
        """Handle a RAG Q&A request."""
        content, sources, llm_resp = await self.rag_skill.answer(message, session_context)
        return AgentResponse(
            content=content,
            sources=sources,
            skill_used="rag",
            model=llm_resp.model,
            provider=llm_resp.provider,
            input_tokens=llm_resp.input_tokens,
            output_tokens=llm_resp.output_tokens,
        )

    async def _handle_ship30(
        self, message: str, session_context: list[dict] | None
    ) -> AgentResponse:
        """Handle a Ship 30 for 30 essay request."""
        # Extract topic from message
        topic = self._extract_topic(message)

        content, sources, llm_resp = await self.ship30_skill.generate_essay(topic, session_context)
        return AgentResponse(
            content=content,
            sources=sources,
            skill_used="ship30",
            model=llm_resp.model,
            provider=llm_resp.provider,
            input_tokens=llm_resp.input_tokens,
            output_tokens=llm_resp.output_tokens,
            artifact_content=content,
            artifact_type="markdown",
            artifact_title=f"Ship 30 Essay: {topic[:50]}",
        )

    async def _handle_artifact(
        self, message: str, session_context: list[dict] | None
    ) -> AgentResponse:
        """Handle an artifact generation request."""
        artifact_type = self.router.detect_artifact_type(message)

        content, title, sanitized = await self.artifact_skill.generate(
            message, artifact_type, session_context
        )

        return AgentResponse(
            content=f"I've generated a {artifact_type} artifact: **{title}**\n\nYou can view it in the artifact panel.",
            sources=[],
            skill_used="artifact",
            model=self.llm.model,
            provider=self.llm.provider,
            artifact_content=content,
            artifact_type=artifact_type,
            artifact_title=title,
            artifact_sanitized=sanitized,
        )

    def _extract_topic(self, message: str) -> str:
        """Extract the essay topic from the user's message."""
        msg_lower = message.lower()

        # Remove common prefixes
        prefixes = [
            "write a ship 30 for 30 essay on",
            "write a ship 30for30 essay on",
            "write a ship30for30 essay about",
            "write an essay on",
            "write an essay about",
            "write a blog post on",
            "write a blog post about",
            "write an article on",
            "write an article about",
            "turn this into an essay about",
            "turn this into an essay on",
            "turn that into an essay",
        ]

        for prefix in prefixes:
            if msg_lower.startswith(prefix):
                return message[len(prefix):].strip()

        # If no prefix matched, use the full message as topic
        return message
