"""SQLAlchemy ORM models for The Lenny Growth Assistant.

Tables: sessions, messages, artifacts, transcript_chunks.
Uses pgvector for embedding storage and similarity search.
"""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base


class Session(Base):
    """Chat session — groups messages into independent conversations."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="New Chat"
    )
    model_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ollama"
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="llama3.1:8b"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    """Single message within a chat session."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False  # 'user', 'assistant', 'system'
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[dict | list] = mapped_column(JSONB, default=list)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="messages")


class Artifact(Base):
    """Generated artifact (Markdown or HTML) linked to a session."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False  # 'markdown', 'html'
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="artifacts")


class TranscriptChunk(Base):
    """Chunked transcript segment with embedding for vector search."""

    __tablename__ = "transcript_chunks"
    __table_args__ = (
        UniqueConstraint("episode_id", "chunk_index", name="uq_episode_chunk"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    episode_id: Mapped[str] = mapped_column(String(100), nullable=False)
    guest: Mapped[str] = mapped_column(String(200), nullable=False)
    episode_title: Mapped[str] = mapped_column(String(500), nullable=False)
    youtube_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
