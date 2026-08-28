"""Application configuration using Pydantic Settings.

All settings are loaded from environment variables or .env file.
Model toggle is controlled via LLM_PROVIDER env var.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for The Lenny Growth Assistant."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Application ───────────────────────────────────────────────────
    APP_NAME: str = "Lenny Growth Assistant"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ─── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://lenny:lenny@localhost:5432/lenny_assistant"

    # ─── LLM Provider Toggle ──────────────────────────────────────────
    LLM_PROVIDER: Literal["ollama", "anthropic", "openai"] = "ollama"

    # ─── Ollama (Local) ───────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # ─── Anthropic (Cloud) ────────────────────────────────────────────
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # ─── OpenAI (Cloud / Embeddings) ─────────────────────────────────
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ─── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ─── Vector Search ────────────────────────────────────────────────
    EMBEDDING_DIMENSION: int = 768
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.5

    # ─── Session / Context ────────────────────────────────────────────
    MAX_SESSION_MESSAGES: int = 50
    MAX_CONTEXT_MESSAGES: int = 10

    # ─── Transcript Data ──────────────────────────────────────────────
    TRANSCRIPT_DATA_DIR: str = "./data/transcripts/episodes"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_cloud_provider(self) -> bool:
        """Check if using a cloud LLM provider."""
        return self.LLM_PROVIDER in ("anthropic", "openai")

    @property
    def current_model_name(self) -> str:
        """Get the active model name based on provider."""
        if self.LLM_PROVIDER == "ollama":
            return self.OLLAMA_MODEL
        elif self.LLM_PROVIDER == "anthropic":
            return self.ANTHROPIC_MODEL
        return self.OPENAI_MODEL


# Singleton instance
settings = Settings()
