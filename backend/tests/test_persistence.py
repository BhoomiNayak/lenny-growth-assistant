"""Persistence tests — ORM models, relationships, cascades."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Artifact, Message, Session


class TestSessionPersistence:
    """Session model CRUD and defaults."""

    async def test_create_session_defaults(self, db_session: AsyncSession):
        session = Session(title="Persist Test")
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert isinstance(session.id, uuid.UUID)
        assert session.title == "Persist Test"
        assert session.model_provider == "ollama"
        assert session.model_name == "llama3.1:8b"
        assert session.created_at is not None

    async def test_update_session(self, db_session: AsyncSession):
        session = Session(title="Original")
        db_session.add(session)
        await db_session.commit()

        session.title = "Modified"
        session.model_provider = "anthropic"
        await db_session.commit()
        await db_session.refresh(session)

        assert session.title == "Modified"
        assert session.model_provider == "anthropic"


class TestMessagePersistence:
    """Message model with sources JSONB."""

    async def test_create_message_with_sources(self, db_session: AsyncSession):
        session = Session(title="Chat")
        db_session.add(session)
        await db_session.commit()

        sources = [
            {"episode_id": "ep-1", "guest": "Jane", "episode_title": "Growth",
             "excerpt": "text", "youtube_url": None, "publish_date": None}
        ]
        message = Message(
            session_id=session.id,
            role="assistant",
            content="Here is an answer.",
            sources=sources,
            latency_ms=1500,
            token_count=42,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        assert message.role == "assistant"
        assert message.sources[0]["guest"] == "Jane"
        assert message.latency_ms == 1500
        assert message.token_count == 42

    async def test_messages_linked_to_session(self, db_session: AsyncSession):
        session = Session(title="Chat")
        db_session.add(session)
        await db_session.commit()

        for i in range(3):
            db_session.add(Message(
                session_id=session.id,
                role="user",
                content=f"Message {i}",
                sources=[],
            ))
        await db_session.commit()

        result = await db_session.execute(
            select(Message).where(Message.session_id == session.id)
        )
        messages = result.scalars().all()
        assert len(messages) == 3


class TestCascadeDelete:
    """Deleting a session cascades to its messages and artifacts."""

    async def test_delete_session_cascades(self, db_session: AsyncSession):
        session = Session(title="To Delete")
        db_session.add(session)
        await db_session.commit()
        session_id = session.id

        db_session.add(Message(
            session_id=session_id, role="user", content="hi", sources=[],
        ))
        db_session.add(Artifact(
            session_id=session_id, type="markdown", title="Doc",
            content="# Doc", sanitized=False,
        ))
        await db_session.commit()

        # Delete the session
        await db_session.delete(session)
        await db_session.commit()

        # Messages and artifacts should be gone
        msg_result = await db_session.execute(
            select(Message).where(Message.session_id == session_id)
        )
        art_result = await db_session.execute(
            select(Artifact).where(Artifact.session_id == session_id)
        )
        assert msg_result.scalars().all() == []
        assert art_result.scalars().all() == []


class TestArtifactPersistence:
    """Artifact model."""

    async def test_create_artifact(self, db_session: AsyncSession):
        session = Session(title="Chat")
        db_session.add(session)
        await db_session.commit()

        artifact = Artifact(
            session_id=session.id,
            type="html",
            title="Slide Deck",
            content="<div>content</div>",
            sanitized=True,
        )
        db_session.add(artifact)
        await db_session.commit()
        await db_session.refresh(artifact)

        assert artifact.type == "html"
        assert artifact.sanitized is True
        assert isinstance(artifact.id, uuid.UUID)
