"""Pytest fixtures for The Lenny Growth Assistant test suite.

Uses a real PostgreSQL + pgvector database (the same engine the app uses)
with tables created/dropped per test session. LLM and embedding calls are
mocked so tests are fast, deterministic, and don't require Ollama.
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Test DB — override before importing app modules
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://lenny:lenny@localhost:5440/lenny_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Session as SessionModel  # noqa: E402
from app.models import Message, Artifact, TranscriptChunk  # noqa: E402


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create a test database engine and set up the schema."""
    eng = create_async_engine(TEST_DATABASE_URL, poolclass=None)

    async with eng.begin() as conn:
        # Ensure pgvector extension + uuid
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Drop any leftover tables from a previous run, then recreate clean
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    # Teardown: drop all tables
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for direct DB tests."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client with the test DB injected."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_session(db_session: AsyncSession) -> SessionModel:
    """Create a sample session in the DB."""
    session = SessionModel(title="Test Chat")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def sample_chunk(db_session: AsyncSession) -> TranscriptChunk:
    """Insert a sample transcript chunk with a fake embedding."""
    # 768-dim embedding — all small values
    embedding = [0.01] * 768
    embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"

    import uuid as _uuid
    from datetime import date

    await db_session.execute(
        text("""
            INSERT INTO transcript_chunks
                (id, episode_id, guest, episode_title, youtube_url, publish_date, chunk_index, content, embedding, metadata)
            VALUES
                (:id, :eid, :guest, :title, :url, :pdate, :idx, :content, cast(:emb as vector), cast(:meta as jsonb))
        """),
        {
            "id": _uuid.uuid4(),
            "eid": "test-guest",
            "guest": "Test Guest",
            "title": "How to Test Growth",
            "url": "https://youtube.com/watch?v=test",
            "pdate": date(2024, 1, 1),
            "idx": 0,
            "content": "Growth teams should focus on activation and retention metrics.",
            "emb": embedding_literal,
            "meta": "{}",
        },
    )
    await db_session.commit()

    result = await db_session.execute(
        text("SELECT * FROM transcript_chunks WHERE episode_id = 'test-guest'")
    )
    return result.fetchone()


class FakeLLMResponse:
    """Mimics LLMResponse for mocking."""

    def __init__(self, content: str):
        self.content = content
        self.model = "test-model"
        self.provider = "test"
        self.input_tokens = 10
        self.output_tokens = 20
