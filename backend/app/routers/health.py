"""Health and readiness endpoints.

/health — simple liveness probe (always returns 200 if app is running)
/health/ready — readiness probe checking all dependencies (DB, Ollama, cloud API)
"""

import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

from app.config import settings
from app.database import check_db_connection
from app.schemas import (
    DependencyStatus,
    HealthResponse,
    ReadinessResponse,
)
from app.utils.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — confirms the application process is running."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness probe — checks all external dependencies."""
    dependencies: dict[str, DependencyStatus] = {}

    # Check database
    dependencies["database"] = await _check_database()

    # Check Ollama (if configured as provider)
    dependencies["ollama"] = await _check_ollama()

    # Check Anthropic (if configured)
    dependencies["anthropic"] = _check_anthropic()

    # Overall status
    critical_deps = [dependencies["database"]]
    if settings.LLM_PROVIDER == "ollama":
        critical_deps.append(dependencies["ollama"])
    elif settings.LLM_PROVIDER == "anthropic":
        critical_deps.append(dependencies["anthropic"])

    all_healthy = all(d.status in ("connected", "available", "configured") for d in critical_deps)

    return ReadinessResponse(
        status="ready" if all_healthy else "degraded",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        dependencies=dependencies,
    )


async def _check_database() -> DependencyStatus:
    """Check PostgreSQL connectivity."""
    start = time.perf_counter()
    try:
        connected = await check_db_connection()
        latency = int((time.perf_counter() - start) * 1000)
        if connected:
            return DependencyStatus(status="connected", latency_ms=latency)
        return DependencyStatus(status="disconnected", reason="Connection check failed")
    except Exception as e:
        return DependencyStatus(status="error", reason=str(e))


async def _check_ollama() -> DependencyStatus:
    """Check if Ollama is reachable and has required models."""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            latency = int((time.perf_counter() - start) * 1000)

            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check if required model is available
                has_chat = any(settings.OLLAMA_MODEL in name for name in model_names)
                has_embed = any(settings.OLLAMA_EMBEDDING_MODEL in name for name in model_names)

                if has_chat and has_embed:
                    return DependencyStatus(status="available", latency_ms=latency)
                missing = []
                if not has_chat:
                    missing.append(settings.OLLAMA_MODEL)
                if not has_embed:
                    missing.append(settings.OLLAMA_EMBEDDING_MODEL)
                return DependencyStatus(
                    status="degraded",
                    latency_ms=latency,
                    reason=f"Missing models: {', '.join(missing)}",
                )
            return DependencyStatus(status="error", reason=f"HTTP {resp.status_code}")
    except httpx.ConnectError:
        return DependencyStatus(status="unavailable", reason="Ollama is not running")
    except Exception as e:
        return DependencyStatus(status="error", reason=str(e))


def _check_anthropic() -> DependencyStatus:
    """Check if Anthropic API key is configured (no live ping to save quota)."""
    if settings.ANTHROPIC_API_KEY:
        return DependencyStatus(status="configured")
    return DependencyStatus(status="unconfigured", reason="ANTHROPIC_API_KEY not set")
