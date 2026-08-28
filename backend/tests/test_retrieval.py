"""Retrieval and chunking tests.

Covers:
- Chunking logic (from the ingestion pipeline)
- RetrievalService vector search (with mocked embeddings, real pgvector DB)
- RetrievalResult -> SourceCitation conversion
- Empty retrieval handling
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval_service import RetrievalService, RetrievalResult
from app.utils.chunking import chunk_text, parse_transcript


class TestChunking:
    """Chunking logic from the ingestion pipeline."""

    def test_chunk_short_text_single_chunk(self):
        text_content = "This is a short paragraph about growth."
        chunks = chunk_text(text_content)
        assert len(chunks) == 1
        assert "growth" in chunks[0]

    def test_chunk_long_text_multiple_chunks(self):
        # Build a long text with many paragraphs
        paragraph = "Growth strategy involves many tactics and experiments. " * 20
        text_content = "\n\n".join([paragraph] * 10)
        chunks = chunk_text(text_content, chunk_size=100, overlap=10)
        assert len(chunks) > 1

    def test_chunk_empty_text(self):
        chunks = chunk_text("")
        assert chunks == []

    def test_chunk_preserves_content(self):
        text_content = "Airbnb focused on activation. Notion used templates."
        chunks = chunk_text(text_content)
        joined = " ".join(chunks)
        assert "Airbnb" in joined
        assert "Notion" in joined


class TestTranscriptParsing:
    """YAML frontmatter parsing."""

    def test_parse_valid_transcript(self, tmp_path):
        content = """---
guest: Test Guest
title: Test Episode
youtube_url: https://youtube.com/test
publish_date: 2024-01-01
---

This is the transcript body with enough content to pass the minimum length check. """ * 5
        f = tmp_path / "transcript.md"
        f.write_text(content, encoding="utf-8")

        result = parse_transcript(f)
        assert result is not None
        assert result["metadata"]["guest"] == "Test Guest"
        assert "transcript body" in result["transcript"]

    def test_parse_too_short_returns_none(self, tmp_path):
        f = tmp_path / "transcript.md"
        f.write_text("---\nguest: X\n---\nshort", encoding="utf-8")
        result = parse_transcript(f)
        assert result is None


class TestRetrievalService:
    """Vector search over the test database."""

    async def test_search_returns_results(self, db_session: AsyncSession, sample_chunk):
        service = RetrievalService(db_session)

        # Mock the embedding to match the stored chunk's embedding closely
        with patch.object(
            service, "_generate_embedding", new=AsyncMock(return_value=[0.01] * 768)
        ):
            results = await service.search("growth teams", top_k=5)

        assert len(results) >= 1
        assert results[0].guest == "Test Guest"
        assert results[0].similarity > 0.9  # Same vector => high similarity

    async def test_search_empty_db_returns_empty(self, db_session: AsyncSession):
        service = RetrievalService(db_session)
        with patch.object(
            service, "_generate_embedding", new=AsyncMock(return_value=[0.5] * 768)
        ):
            results = await service.search("anything", top_k=5)
        assert results == []

    async def test_get_context_for_query_formats_output(
        self, db_session: AsyncSession, sample_chunk
    ):
        service = RetrievalService(db_session)
        with patch.object(
            service, "_generate_embedding", new=AsyncMock(return_value=[0.01] * 768)
        ):
            context, citations = await service.get_context_for_query("growth")

        assert "Test Guest" in context
        assert len(citations) >= 1
        assert citations[0].guest == "Test Guest"

    async def test_get_context_empty_returns_empty_string(self, db_session: AsyncSession):
        service = RetrievalService(db_session)
        with patch.object(
            service, "_generate_embedding", new=AsyncMock(return_value=[0.9] * 768)
        ):
            context, citations = await service.get_context_for_query("nothing")
        assert context == ""
        assert citations == []


class TestRetrievalResult:
    """RetrievalResult -> SourceCitation conversion."""

    def test_to_citation(self):
        result = RetrievalResult(
            content="A" * 300,  # long content
            episode_id="ep-1",
            guest="Jane Doe",
            episode_title="Growth 101",
            youtube_url="https://youtube.com/x",
            publish_date="2024-01-01",
            chunk_index=0,
            similarity=0.85,
        )
        citation = result.to_citation()
        assert citation.guest == "Jane Doe"
        assert citation.episode_title == "Growth 101"
        assert citation.excerpt.endswith("...")  # truncated
        assert len(citation.excerpt) <= 205
