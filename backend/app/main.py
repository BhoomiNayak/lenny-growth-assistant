"""FastAPI application factory for The Lenny Growth Assistant.

Creates the app with lifespan events, CORS, error handlers, and routers.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import ErrorResponse, ErrorDetail
from app.utils.errors import AppError
from app.utils.logging import get_logger, setup_logging
from app.utils.middleware import RequestLoggingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    setup_logging()
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        llm_provider=settings.LLM_PROVIDER,
        model=settings.current_model_name,
    )

    # Wait for the database to be reachable (handles Docker startup races)
    from app.database import wait_for_db

    db_ready = await wait_for_db()
    if not db_ready:
        logger.error("startup.database_unavailable", note="API starting in degraded mode")

    yield
    # Shutdown
    logger.info("application_shutting_down")
    from app.database import engine
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered assistant grounded in Lenny's Podcast transcripts",
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    # ─── Middleware ────────────────────────────────────────────────────
    # Request logging with correlation IDs (added first = outermost layer)
    app.add_middleware(RequestLoggingMiddleware)

    # ─── CORS ──────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # NOTE: Authentication is intentionally omitted for this single-tenant
    # local demo (see PRD assumption A2). In production, add OAuth2/API key
    # middleware here. Rate limiting (e.g., slowapi) would also be added.

    # ─── Exception Handlers ────────────────────────────────────────────
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.error(
            "application_error",
            code=exc.code,
            message=exc.message,
            path=str(request.url.path),
            retryable=exc.retryable,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    retryable=exc.retryable,
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_error",
            path=str(request.url.path),
            error_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred.",
                    retryable=True,
                )
            ).model_dump(),
        )

    # ─── Routers ───────────────────────────────────────────────────────
    from app.routers.health import router as health_router
    from app.routers.sessions import router as sessions_router
    from app.routers.messages import router as messages_router
    from app.routers.artifacts import router as artifacts_router
    from app.routers.config import router as config_router

    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(artifacts_router)
    app.include_router(config_router)

    return app


# Application instance
app = create_app()
