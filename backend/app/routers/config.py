"""Configuration endpoints — model listing and session model switching.

GET  /api/v1/config/models         — List available providers and models
PUT  /api/v1/sessions/{id}/model   — Switch model for a session
"""

import uuid

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Session
from app.schemas import (
    ModelConfigResponse,
    ModelSwitchRequest,
    ProviderConfig,
    SessionResponse,
)
from app.utils.errors import SessionNotFoundError, LLMUnavailableError
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/v1", tags=["config"])
logger = get_logger(__name__)


@router.get("/config/models", response_model=ModelConfigResponse)
async def list_models() -> ModelConfigResponse:
    """List all configured LLM providers and their status."""
    providers: list[ProviderConfig] = []

    # Check Ollama
    ollama_available = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_available = True
    except Exception:
        pass

    providers.append(ProviderConfig(
        provider="ollama",
        model=settings.OLLAMA_MODEL,
        available=ollama_available,
        reason=None if ollama_available else "Ollama is not running",
    ))

    # Check Anthropic
    anthropic_configured = bool(settings.ANTHROPIC_API_KEY)
    providers.append(ProviderConfig(
        provider="anthropic",
        model=settings.ANTHROPIC_MODEL,
        available=anthropic_configured,
        reason=None if anthropic_configured else "ANTHROPIC_API_KEY not set",
    ))

    # Check OpenAI
    openai_configured = bool(settings.OPENAI_API_KEY)
    providers.append(ProviderConfig(
        provider="openai",
        model="gpt-4o",
        available=openai_configured,
        reason=None if openai_configured else "OPENAI_API_KEY not set",
    ))

    return ModelConfigResponse(
        current_provider=settings.LLM_PROVIDER,
        current_model=settings.current_model_name,
        providers=providers,
    )


@router.put("/sessions/{session_id}/model", response_model=SessionResponse)
async def switch_session_model(
    session_id: uuid.UUID,
    body: ModelSwitchRequest,
    db: AsyncSession = Depends(get_db),
) -> Session:
    """Switch the LLM provider and model for a specific session."""
    session = await db.get(Session, session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))

    # Validate provider availability
    if body.provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if resp.status_code != 200:
                    raise LLMUnavailableError("ollama", "Ollama returned an error")
        except httpx.ConnectError:
            raise LLMUnavailableError("ollama", "Ollama is not running")
    elif body.provider == "anthropic" and not settings.ANTHROPIC_API_KEY:
        raise LLMUnavailableError("anthropic", "ANTHROPIC_API_KEY not configured")
    elif body.provider == "openai" and not settings.OPENAI_API_KEY:
        raise LLMUnavailableError("openai", "OPENAI_API_KEY not configured")

    # Update session
    session.model_provider = body.provider
    session.model_name = body.model
    await db.flush()
    await db.refresh(session)

    logger.info(
        "session.model_switched",
        session_id=str(session_id),
        provider=body.provider,
        model=body.model,
    )

    return session
