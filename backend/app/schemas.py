"""Pydantic schemas for API request/response validation.

Strict validation, clear contracts, no leaking of internal details.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ─── Source Citation ───────────────────────────────────────────────────────────


class SourceCitation(BaseModel):
    """A citation referencing a specific transcript chunk."""

    episode_id: str
    guest: str
    episode_title: str
    youtube_url: str | None = None
    publish_date: str | None = None
    excerpt: str


# ─── Session Schemas ───────────────────────────────────────────────────────────


class SessionCreate(BaseModel):
    """Request to create a new chat session."""

    title: str | None = Field(None, max_length=255)


class SessionUpdate(BaseModel):
    """Request to update session metadata."""

    model_config = ConfigDict(protected_namespaces=())

    title: str | None = Field(None, max_length=255)
    model_provider: Literal["ollama", "anthropic", "openai"] | None = None
    model_name: str | None = Field(None, max_length=100)


class SessionResponse(BaseModel):
    """Session data returned to the client."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    title: str
    model_provider: str
    model_name: str
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""

    sessions: list[SessionResponse]
    total: int


# ─── Message Schemas ───────────────────────────────────────────────────────────


class MessageCreate(BaseModel):
    """Request to send a message in a session."""

    content: str = Field(..., min_length=1, max_length=10000)
    stream: bool = False


class MessageResponse(BaseModel):
    """Message data returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: Literal["user", "assistant", "system"]
    content: str
    sources: list[SourceCitation] = []
    latency_ms: int | None = None
    token_count: int | None = None
    created_at: datetime


class MessageListResponse(BaseModel):
    """List of messages for a session."""

    messages: list[MessageResponse]
    total: int


# ─── Artifact Schemas ──────────────────────────────────────────────────────────


class ArtifactCreate(BaseModel):
    """Request to generate an artifact."""

    type: Literal["markdown", "html"] = "markdown"
    prompt: str = Field(..., min_length=1, max_length=5000)


class ArtifactResponse(BaseModel):
    """Artifact data returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    type: str
    title: str
    content: str
    sanitized: bool
    created_at: datetime


class ArtifactListResponse(BaseModel):
    """List of artifacts for a session."""

    artifacts: list[ArtifactResponse]


# ─── Model Config Schemas ─────────────────────────────────────────────────────


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    provider: str
    model: str
    available: bool
    reason: str | None = None


class ModelConfigResponse(BaseModel):
    """Current model configuration and available providers."""

    model_config = ConfigDict(protected_namespaces=())

    current_provider: str
    current_model: str
    providers: list[ProviderConfig]


class ModelSwitchRequest(BaseModel):
    """Request to switch the model for a session."""

    model_config = ConfigDict(protected_namespaces=())

    provider: Literal["ollama", "anthropic", "openai"]
    model: str = Field(..., max_length=100)


# ─── Health Schemas ────────────────────────────────────────────────────────────


class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    status: str
    latency_ms: int | None = None
    reason: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    """Readiness check with dependency details."""

    status: str
    version: str
    timestamp: datetime
    dependencies: dict[str, DependencyStatus]


# ─── Error Schemas ─────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Structured error response."""

    code: str
    message: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    """Wrapper for error responses."""

    error: ErrorDetail


# ─── Streaming Event Schemas ──────────────────────────────────────────────────


class StreamEvent(BaseModel):
    """SSE event for streaming responses."""

    type: Literal["start", "token", "sources", "done", "artifact", "error"]
    content: str | None = None
    message_id: uuid.UUID | None = None
    sources: list[SourceCitation] | None = None
    artifact_id: uuid.UUID | None = None
    title: str | None = None
    latency_ms: int | None = None
    token_count: int | None = None
    code: str | None = None
