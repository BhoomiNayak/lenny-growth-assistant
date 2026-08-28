"""Retrieval service for vector search over transcript chunks.

Generates query embeddings via Ollama/OpenAI, performs cosine similarity
search in pgvector, and returns results with source citations.
"""

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas import SourceCitation
from app.utils.errors import RetrievalError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RetrievalResult:
    """A single retrieval result with content and citation metadata."""

    def __init__(
        self,
        content: str,
        episode_id: str,
        guest: str,
        episode_title: str,
        youtube_url: str | None,
        publish_date: str | None,
        chunk_index: int,
        similarity: float,
    ):
        self.content = content
        self.episode_id = episode_id
        self.guest = guest
        self.episode_title = episode_title
        self.youtube_url = youtube_url
        self.publish_date = publish_date
        self.chunk_index = chunk_index
        self.similarity = similarity

    def to_citation(self) -> SourceCitation:
        """Convert to a SourceCitation schema for API responses."""
        # Use first ~200 chars as excerpt
        excerpt = self.content[:200].strip()
        if len(self.content) > 200:
            excerpt += "..."

        return SourceCitation(
            episode_id=self.episode_id,
            guest=self.guest,
            episode_title=self.episode_title,
            youtube_url=self.youtube_url,
            publish_date=self.publish_date,
            excerpt=excerpt,
        )


class RetrievalService:
    """Handles embedding generation and vector similarity search."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """Search transcript chunks by semantic similarity.

        Args:
            query: User's question or search query.
            top_k: Number of results to return (default from config).
            similarity_threshold: Minimum cosine similarity (default from config).

        Returns:
            List of RetrievalResult ordered by similarity (highest first).

        Raises:
            RetrievalError: If embedding generation or search fails.
        """
        top_k = top_k or settings.RETRIEVAL_TOP_K
        similarity_threshold = similarity_threshold or settings.RETRIEVAL_SIMILARITY_THRESHOLD

        # Generate query embedding
        query_embedding = await self._generate_embedding(query)
        if not query_embedding:
            raise RetrievalError("Failed to generate query embedding")

        # Perform vector search
        results = await self._vector_search(query_embedding, top_k, similarity_threshold)

        logger.info(
            "retrieval.search",
            query=query[:100],
            top_k=top_k,
            results_count=len(results),
        )

        return results

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for a single text using configured provider."""
        try:
            if settings.LLM_PROVIDER == "ollama" or not settings.OPENAI_API_KEY:
                return await self._embed_ollama(text)
            else:
                return await self._embed_openai(text)
        except Exception as e:
            logger.error("retrieval.embedding_failed", error=str(e))
            raise RetrievalError(f"Embedding generation failed: {e}")

    async def _embed_ollama(self, text: str) -> list[float] | None:
        """Generate embedding via Ollama."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embed",
                json={"model": settings.OLLAMA_EMBEDDING_MODEL, "input": text[:8000]},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [[]])
            return embeddings[0] if embeddings and embeddings[0] else None

    async def _embed_openai(self, text: str) -> list[float] | None:
        """Generate embedding via OpenAI."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": settings.OPENAI_EMBEDDING_MODEL,
                    "input": text[:8000],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    async def _vector_search(
        self,
        embedding: list[float],
        top_k: int,
        similarity_threshold: float,
    ) -> list[RetrievalResult]:
        """Perform cosine similarity search in pgvector."""
        # pgvector cosine distance: 1 - cosine_similarity
        # So we want (1 - distance) >= threshold, i.e., distance <= (1 - threshold)
        max_distance = 1.0 - similarity_threshold

        query = text("""
            SELECT
                content,
                episode_id,
                guest,
                episode_title,
                youtube_url,
                CAST(publish_date AS text) AS publish_date,
                chunk_index,
                1 - (embedding <=> CAST(:embedding AS vector)) as similarity
            FROM transcript_chunks
            WHERE embedding IS NOT NULL
              AND (1 - (embedding <=> CAST(:embedding AS vector))) >= :threshold
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        embedding_str = str(embedding)

        result = await self.db.execute(
            query,
            {
                "embedding": embedding_str,
                "threshold": similarity_threshold,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()

        return [
            RetrievalResult(
                content=row[0],
                episode_id=row[1],
                guest=row[2],
                episode_title=row[3],
                youtube_url=row[4],
                publish_date=row[5],
                chunk_index=row[6],
                similarity=row[7],
            )
            for row in rows
        ]

    async def get_context_for_query(
        self,
        query: str,
        top_k: int | None = None,
    ) -> tuple[str, list[SourceCitation]]:
        """Convenience method: search and format results for LLM context.

        Returns:
            Tuple of (formatted_context_string, list_of_citations)
        """
        results = await self.search(query, top_k=top_k)

        if not results:
            return "", []

        # Format context for the LLM prompt
        context_parts = []
        citations = []
        seen_episodes = set()

        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}: \"{result.episode_title}\" — {result.guest}]\n"
                f"{result.content}\n"
            )
            # Deduplicate citations by episode
            if result.episode_id not in seen_episodes:
                citations.append(result.to_citation())
                seen_episodes.add(result.episode_id)

        formatted_context = "\n---\n".join(context_parts)
        return formatted_context, citations
