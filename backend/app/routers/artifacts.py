"""Artifact endpoints — generate, list, and retrieve artifacts.

POST  /api/v1/sessions/{id}/artifacts  — Generate a new artifact
GET   /api/v1/sessions/{id}/artifacts  — List artifacts for a session
GET   /api/v1/artifacts/{id}           — Get a single artifact
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.skills.artifact_skill import ArtifactSkill
from app.database import get_db
from app.models import Artifact, Message, Session
from app.schemas import (
    ArtifactCreate,
    ArtifactListResponse,
    ArtifactResponse,
)
from app.services.llm_service import LLMService
from app.utils.errors import ArtifactNotFoundError, SessionNotFoundError
from app.utils.logging import get_logger

router = APIRouter(tags=["artifacts"])
logger = get_logger(__name__)


@router.post(
    "/api/v1/sessions/{session_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=201,
)
async def generate_artifact(
    session_id: uuid.UUID,
    body: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
) -> Artifact:
    """Generate a new artifact from session context."""
    # Verify session exists
    session = await db.get(Session, session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))

    # Get session messages for context
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    context_messages = [
        {"role": m.role, "content": m.content}
        for m in reversed(result.scalars().all())
    ]

    # Generate artifact
    llm = LLMService(provider=session.model_provider, model=session.model_name)
    skill = ArtifactSkill(llm)
    content, title, sanitized = await skill.generate(
        body.prompt, body.type, context_messages
    )

    # Store artifact
    artifact = Artifact(
        session_id=session_id,
        type=body.type,
        title=title,
        content=content,
        sanitized=sanitized,
    )
    db.add(artifact)
    await db.flush()
    await db.refresh(artifact)

    logger.info(
        "artifact.created",
        artifact_id=str(artifact.id),
        session_id=str(session_id),
        type=body.type,
        title=title[:50],
    )

    return artifact


@router.get(
    "/api/v1/sessions/{session_id}/artifacts",
    response_model=ArtifactListResponse,
)
async def list_artifacts(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all artifacts for a session."""
    session = await db.get(Session, session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))

    stmt = (
        select(Artifact)
        .where(Artifact.session_id == session_id)
        .order_by(Artifact.created_at.desc())
    )
    result = await db.execute(stmt)
    artifacts = result.scalars().all()

    return {"artifacts": artifacts}


@router.get("/api/v1/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Artifact:
    """Get a single artifact by ID."""
    artifact = await db.get(Artifact, artifact_id)
    if not artifact:
        raise ArtifactNotFoundError(str(artifact_id))
    return artifact
