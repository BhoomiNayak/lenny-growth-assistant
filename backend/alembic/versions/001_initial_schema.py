"""Initial schema — sessions, messages, artifacts, transcript_chunks.

Revision ID: 001
Revises: None
Create Date: 2026-08-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("title", sa.String(255), nullable=False, server_default="New Chat"),
        sa.Column("model_provider", sa.String(50), nullable=False, server_default="ollama"),
        sa.Column("model_name", sa.String(100), nullable=False, server_default="llama3.1:8b"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Messages table
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", JSONB, server_default="[]"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_messages_session_id", "messages", ["session_id"])

    # Artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sanitized", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_artifacts_session_id", "artifacts", ["session_id"])

    # Transcript chunks table with vector embedding
    op.create_table(
        "transcript_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("episode_id", sa.String(100), nullable=False),
        sa.Column("guest", sa.String(200), nullable=False),
        sa.Column("episode_title", sa.String(500), nullable=False),
        sa.Column("youtube_url", sa.String(500), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("episode_id", "chunk_index", name="uq_episode_chunk"),
    )
    op.create_index("idx_transcript_chunks_episode", "transcript_chunks", ["episode_id"])

    # Add vector column separately (Alembic doesn't natively support pgvector type in create_table)
    op.execute("ALTER TABLE transcript_chunks ADD COLUMN embedding vector(768)")

    # NOTE: The IVFFlat approximate-search index is intentionally NOT created here.
    # IVFFlat computes its cluster centroids at index-creation time. Building it on
    # an empty table produces degenerate clusters, causing index-scan queries
    # (ORDER BY embedding <=> ... LIMIT k) to return 0 rows. The index is created
    # by the ingestion script AFTER data is loaded (scripts/ingest_transcripts.py).
    # Until then, exact (sequential-scan) cosine search is used — accurate and fast
    # for our corpus size (~15k chunks).


def downgrade() -> None:
    op.drop_table("transcript_chunks")
    op.drop_table("artifacts")
    op.drop_table("messages")
    op.drop_table("sessions")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
