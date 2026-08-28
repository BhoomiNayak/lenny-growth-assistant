"""Message endpoints — send messages and get conversation history.

POST  /api/v1/sessions/{id}/messages  — Send message (sync or SSE stream)
GET   /api/v1/sessions/{id}/messages  — List messages for a session
"""

import json
import time
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentOrchestrator
from app.database import get_db, async_session_factory
from app.models import Artifact, Message, Session
from app.schemas import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    SourceCitation,
)
from app.utils.errors import SessionNotFoundError
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/v1/sessions", tags=["messages"])
logger = get_logger(__name__)


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: uuid.UUID,
    body: MessageCreate,
):
    """Send a message and get the AI response.

    If stream=true, returns Server-Sent Events instead of JSON.
    """
    # Verify session exists (short-lived session)
    async with async_session_factory() as db:
        existing_session = await db.get(Session, session_id)
        if not existing_session:
            raise SessionNotFoundError(str(session_id))

    # Handle streaming (manages its own short-lived DB sessions)
    if body.stream:
        return StreamingResponse(
            _stream_response(session_id, body.content),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Sync response (uses short-lived session with commit/rollback)
    async with async_session_factory() as db:
        try:
            session = await db.get(Session, session_id)
            result = await _sync_response(session_id, session, body.content, db)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


async def _sync_response(
    session_id: uuid.UUID,
    session: Session,
    content: str,
    db: AsyncSession,
) -> Message:
    """Process message synchronously and return complete response."""
    start_time = time.time()

    # Save user message
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=content,
    )
    db.add(user_msg)
    await db.flush()

    # Get session context (last N messages)
    context_stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    context_result = await db.execute(context_stmt)
    context_messages = [
        {"role": m.role, "content": m.content}
        for m in reversed(context_result.scalars().all())
    ]

    # Process through agent
    agent = AgentOrchestrator(
        db,
        provider=session.model_provider,
        model=session.model_name,
    )
    response = await agent.process_message(content, context_messages)

    latency_ms = int((time.time() - start_time) * 1000)

    # Save assistant message
    sources_data = [s.model_dump() for s in response.sources]
    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=response.content,
        sources=sources_data,
        latency_ms=latency_ms,
        token_count=response.output_tokens,
    )
    db.add(assistant_msg)

    # If an artifact was generated, save it
    if response.artifact_content:
        artifact = Artifact(
            session_id=session_id,
            type=response.artifact_type or "markdown",
            title=response.artifact_title or "Untitled",
            content=response.artifact_content,
            sanitized=response.artifact_sanitized,
        )
        db.add(artifact)

    await db.flush()
    await db.refresh(assistant_msg)

    # Update session title if this is the first message
    msg_count_stmt = select(func.count()).select_from(Message).where(
        Message.session_id == session_id
    )
    msg_count = (await db.execute(msg_count_stmt)).scalar() or 0
    if msg_count <= 2:
        session.title = content[:50].strip()
        await db.flush()

    logger.info(
        "message.processed",
        session_id=str(session_id),
        skill=response.skill_used,
        latency_ms=latency_ms,
        sources=len(response.sources),
    )

    return assistant_msg


async def _stream_response(
    session_id: uuid.UUID,
    content: str,
):
    """Stream response as Server-Sent Events.

    DB session strategy: commit user message immediately, then release the
    connection during LLM streaming, then open a new short-lived session
    to save the assistant message. This prevents pool exhaustion.
    """
    import time as _time

    start_time = _time.time()

    # Phase 1: Save user message (short-lived session)
    provider: str | None = None
    model_name: str | None = None
    async with async_session_factory() as db:
        session = await db.get(Session, session_id)
        if not session:
            yield f"data: {json.dumps({'type': 'error', 'code': 'NOT_FOUND', 'message': 'Session not found'})}\n\n"
            return

        provider = session.model_provider
        model_name = session.model_name

        user_msg = Message(
            session_id=session_id,
            role="user",
            content=content,
        )
        db.add(user_msg)
        await db.commit()

    # Phase 2: Load session context (short-lived session)
    async with async_session_factory() as db:
        context_stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        context_result = await db.execute(context_stmt)
        context_messages = [
            {"role": m.role, "content": m.content}
            for m in reversed(context_result.scalars().all())
        ]

    # Phase 3: Pre-retrieve context (short-lived session, released before streaming)
    context_text: str | None = None
    citations: list[SourceCitation] = []
    async with async_session_factory() as db:
        agent = AgentOrchestrator(db, provider=provider, model=model_name)
        skill_name = agent.router.route(content, context_messages)

        if skill_name == "rag":
            context_text, citations = await agent.retrieval.get_context_for_query(content)
        elif skill_name == "ship30":
            topic = agent._extract_topic(content)
            context_text, citations = await agent.retrieval.get_context_for_query(topic, top_k=8)
    # Session closed — connection returned to pool before LLM streaming begins

    # Phase 4: Stream LLM tokens (no DB session held)
    agent = AgentOrchestrator(provider=provider, model=model_name)
    msg_id = uuid.uuid4()
    yield f"data: {json.dumps({'type': 'start', 'message_id': str(msg_id)})}\n\n"

    full_content = ""
    skill_used = "rag"
    artifact_data: dict | None = None

    try:
        async for token, is_done, done_citations, skill, artifact_data in (
            agent.process_message_stream(content, context_messages, context_text, citations)
        ):
            if is_done:
                citations = done_citations or []
                skill_used = skill
            else:
                full_content += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
    except Exception as e:
        logger.error("message.stream_error", error=str(e), error_type=type(e).__name__)
        yield f"data: {json.dumps({'type': 'error', 'code': 'STREAM_ERROR', 'message': 'An error occurred while generating the response.'})}\n\n"
        return

    latency_ms = int((_time.time() - start_time) * 1000)

    # Send sources
    if citations:
        yield f"data: {json.dumps({'type': 'sources', 'sources': [c.model_dump() for c in citations]})}\n\n"

    # Phase 5: Save assistant message (short-lived session)
    try:
        async with async_session_factory() as db:
            sources_data = [s.model_dump() for s in citations]
            assistant_msg = Message(
                session_id=session_id,
                role="assistant",
                content=full_content,
                sources=sources_data,
                latency_ms=latency_ms,
            )
            db.add(assistant_msg)

            # If an artifact was generated, save it
            if artifact_data:
                artifact = Artifact(
                    session_id=session_id,
                    type=artifact_data.get("type", "markdown"),
                    title=artifact_data.get("title", "Untitled"),
                    content=artifact_data.get("content", ""),
                    sanitized=artifact_data.get("sanitized", False),
                )
                db.add(artifact)

            # Update session title on first message
            msg_count_stmt = select(func.count()).select_from(Message).where(
                Message.session_id == session_id
            )
            msg_count = (await db.execute(msg_count_stmt)).scalar() or 0
            if msg_count <= 2:
                session_obj = await db.get(Session, session_id)
                if session_obj:
                    session_obj.title = content[:50].strip()

            await db.commit()
    except Exception as e:
        logger.error("message.save_error", error=str(e))

    # Send done event
    yield f"data: {json.dumps({'type': 'done', 'message_id': str(msg_id), 'latency_ms': latency_ms})}\n\n"

    logger.info(
        "message.streamed",
        session_id=str(session_id),
        skill=skill_used,
        latency_ms=latency_ms,
    )


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List messages for a session, oldest first."""
    # Verify session exists
    session = await db.get(Session, session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))

    # Count total
    count_stmt = (
        select(func.count())
        .select_from(Message)
        .where(Message.session_id == session_id)
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch messages
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return {"messages": messages, "total": total}
