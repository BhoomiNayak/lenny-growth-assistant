"""Session CRUD endpoints.

POST   /api/v1/sessions       — Create a new chat session
GET    /api/v1/sessions       — List sessions (paginated)
GET    /api/v1/sessions/{id}  — Get a single session
PATCH  /api/v1/sessions/{id}  — Update session (title, model)
DELETE /api/v1/sessions/{id}  — Delete session
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Session
from app.schemas import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from app.utils.errors import SessionNotFoundError
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
logger = get_logger(__name__)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate | None = None,
    db: AsyncSession = Depends(get_db),
) -> Session:
    """Create a new chat session."""
    session = Session(
        title=body.title if body and body.title else "New Chat",
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    logger.info("session.created", session_id=str(session.id), title=session.title)
    return session


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all sessions, newest first."""
    # Count total
    count_stmt = select(func.count()).select_from(Session)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch page
    stmt = (
        select(Session)
        .order_by(Session.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return {"sessions": sessions, "total": total}


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Session:
    """Get a single session by ID."""
    session = await db.get(Session, session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
) -> Session:
    """Update session title or model configuration."""
    session = await db.get(Session, session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))

    if body.title is not None:
        session.title = body.title
    if body.model_provider is not None:
        session.model_provider = body.model_provider
    if body.model_name is not None:
        session.model_name = body.model_name

    await db.flush()
    await db.refresh(session)

    logger.info("session.updated", session_id=str(session_id))
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a session and all associated messages/artifacts."""
    session = await db.get(Session, session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))

    await db.delete(session)
    logger.info("session.deleted", session_id=str(session_id))
