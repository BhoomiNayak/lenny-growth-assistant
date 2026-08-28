"""Request logging middleware with correlation IDs.

Assigns a unique correlation ID to each request, binds it to the structlog
context so all logs within a request are traceable, and logs request/response
with timing for observability.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs each request with a correlation ID and timing.

    - Generates (or reuses inbound) X-Correlation-ID
    - Binds it to structlog contextvars so downstream logs include it
    - Logs api.request on entry and api.response on exit with duration
    - Adds X-Correlation-ID to the response headers
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Reuse client-provided correlation ID if present, else generate one
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Bind to structlog context — every log in this request carries it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        start = time.perf_counter()

        logger.info(
            "api.request",
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "api.request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "api.response",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        # Surface the correlation ID to the client for support/debugging
        response.headers["X-Correlation-ID"] = correlation_id
        return response
