"""Custom exception classes for structured error handling.

Each exception maps to a specific HTTP status code, error code,
and retryable flag for the client.
"""


class AppError(Exception):
    """Base application error with structured metadata."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        retryable: bool = False,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(message)


class LLMUnavailableError(AppError):
    """Raised when the configured LLM provider is not reachable."""

    def __init__(self, provider: str, reason: str | None = None):
        detail = reason or f"{provider} is currently unavailable"
        super().__init__(
            message=f"{detail}. Please try another model.",
            code="LLM_UNAVAILABLE",
            status_code=503,
            retryable=True,
        )


class LLMTimeoutError(AppError):
    """Raised when an LLM request exceeds the configured timeout."""

    def __init__(self, provider: str, timeout_seconds: int):
        super().__init__(
            message=f"{provider} did not respond within {timeout_seconds}s. Please try again.",
            code="LLM_TIMEOUT",
            status_code=504,
            retryable=True,
        )


class RetrievalError(AppError):
    """Raised when vector search fails unexpectedly."""

    def __init__(self, reason: str | None = None):
        super().__init__(
            message=reason or "Unable to search knowledge base. Please try again.",
            code="RETRIEVAL_FAILED",
            status_code=500,
            retryable=True,
        )


class EmptyRetrievalError(AppError):
    """Raised when retrieval returns no relevant results."""

    def __init__(self):
        super().__init__(
            message="I don't have enough information to answer that confidently.",
            code="NO_RELEVANT_SOURCES",
            status_code=200,
            retryable=False,
        )


class SessionNotFoundError(AppError):
    """Raised when a requested session does not exist."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} not found.",
            code="SESSION_NOT_FOUND",
            status_code=404,
            retryable=False,
        )


class ArtifactNotFoundError(AppError):
    """Raised when a requested artifact does not exist."""

    def __init__(self, artifact_id: str):
        super().__init__(
            message=f"Artifact {artifact_id} not found.",
            code="ARTIFACT_NOT_FOUND",
            status_code=404,
            retryable=False,
        )


class ValidationError(AppError):
    """Raised for custom validation failures beyond Pydantic."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            retryable=False,
        )


class DatabaseError(AppError):
    """Raised when a database operation fails."""

    def __init__(self, reason: str | None = None):
        super().__init__(
            message=reason or "Database operation failed. Please try again.",
            code="DATABASE_ERROR",
            status_code=500,
            retryable=True,
        )
