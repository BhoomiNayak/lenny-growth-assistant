"""LLM provider factory — unified interface for Ollama, Anthropic, and OpenAI.

Provides a single `generate()` method that routes to the active provider
based on config. Supports streaming via async generators.
"""

from dataclasses import dataclass
from typing import AsyncGenerator

import httpx

from app.config import settings
from app.utils.errors import LLMUnavailableError, LLMTimeoutError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Timeout for LLM requests (seconds)
LLM_TIMEOUT = 300.0


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMService:
    """Unified LLM interface with provider switching."""

    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.current_model_name

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a completion from the configured LLM provider.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum output tokens.

        Returns:
            LLMResponse with content and metadata.

        Raises:
            LLMUnavailableError: Provider not reachable or misconfigured.
            LLMTimeoutError: Request exceeded timeout.
        """
        logger.info(
            "llm.request",
            provider=self.provider,
            model=self.model,
            messages_count=len(messages),
        )

        if self.provider == "ollama":
            return await self._generate_ollama(messages, temperature, max_tokens)
        elif self.provider == "anthropic":
            return await self._generate_anthropic(messages, temperature, max_tokens)
        elif self.provider == "openai":
            return await self._generate_openai(messages, temperature, max_tokens)
        else:
            raise LLMUnavailableError(self.provider, f"Unknown provider: {self.provider}")

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the configured LLM provider.

        Yields individual tokens/chunks as they arrive.
        """
        if self.provider == "ollama":
            async for token in self._stream_ollama(messages, temperature, max_tokens):
                yield token
        elif self.provider == "anthropic":
            async for token in self._stream_anthropic(messages, temperature, max_tokens):
                yield token
        elif self.provider == "openai":
            async for token in self._stream_openai(messages, temperature, max_tokens):
                yield token
        else:
            raise LLMUnavailableError(self.provider, f"Unknown provider: {self.provider}")

    # ─── Ollama ────────────────────────────────────────────────────────────────

    async def _generate_ollama(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> LLMResponse:
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_ctx": 8192,
                        },
                    },
                )
                if resp.status_code != 200:
                    error_text = resp.text[:200]
                    raise LLMUnavailableError("ollama", f"Ollama error {resp.status_code}: {error_text}")

                data = resp.json()

                content = data.get("message", {}).get("content", "")
                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider="ollama",
                    input_tokens=data.get("prompt_eval_count"),
                    output_tokens=data.get("eval_count"),
                )
        except httpx.ConnectError:
            raise LLMUnavailableError("ollama", "Ollama is not running")
        except httpx.TimeoutException:
            raise LLMTimeoutError("ollama", int(LLM_TIMEOUT))

    async def _stream_ollama(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_ctx": 8192,
                        },
                    },
                ) as resp:
                    resp.raise_for_status()
                    import json
                    async for line in resp.aiter_lines():
                        if line.strip():
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if chunk.get("done"):
                                break
        except httpx.ConnectError:
            raise LLMUnavailableError("ollama", "Ollama is not running")
        except httpx.TimeoutException:
            raise LLMTimeoutError("ollama", int(LLM_TIMEOUT))

    # ─── Anthropic ─────────────────────────────────────────────────────────────

    async def _generate_anthropic(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> LLMResponse:
        if not settings.ANTHROPIC_API_KEY:
            raise LLMUnavailableError("anthropic", "ANTHROPIC_API_KEY not configured")

        # Separate system message from conversation
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                body = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": chat_messages,
                }
                if system_msg:
                    body["system"] = system_msg

                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()

                content = data.get("content", [{}])[0].get("text", "")
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider="anthropic",
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                )
        except httpx.ConnectError:
            raise LLMUnavailableError("anthropic", "Cannot reach Anthropic API")
        except httpx.TimeoutException:
            raise LLMTimeoutError("anthropic", int(LLM_TIMEOUT))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMUnavailableError("anthropic", "Invalid ANTHROPIC_API_KEY")
            raise LLMUnavailableError("anthropic", f"API error: {e.response.status_code}")

    async def _stream_anthropic(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        if not settings.ANTHROPIC_API_KEY:
            raise LLMUnavailableError("anthropic", "ANTHROPIC_API_KEY not configured")

        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                body = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": chat_messages,
                    "stream": True,
                }
                if system_msg:
                    body["system"] = system_msg

                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=body,
                ) as resp:
                    resp.raise_for_status()
                    import json
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                text = data.get("delta", {}).get("text", "")
                                if text:
                                    yield text
                            elif data.get("type") == "message_stop":
                                break
        except httpx.ConnectError:
            raise LLMUnavailableError("anthropic", "Cannot reach Anthropic API")
        except httpx.TimeoutException:
            raise LLMTimeoutError("anthropic", int(LLM_TIMEOUT))

    # ─── OpenAI ────────────────────────────────────────────────────────────────

    async def _generate_openai(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> LLMResponse:
        if not settings.OPENAI_API_KEY:
            raise LLMUnavailableError("openai", "OPENAI_API_KEY not configured")

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider="openai",
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                )
        except httpx.ConnectError:
            raise LLMUnavailableError("openai", "Cannot reach OpenAI API")
        except httpx.TimeoutException:
            raise LLMTimeoutError("openai", int(LLM_TIMEOUT))

    async def _stream_openai(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        if not settings.OPENAI_API_KEY:
            raise LLMUnavailableError("openai", "OPENAI_API_KEY not configured")

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    import json
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            data = json.loads(line[6:])
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
        except httpx.ConnectError:
            raise LLMUnavailableError("openai", "Cannot reach OpenAI API")
        except httpx.TimeoutException:
            raise LLMTimeoutError("openai", int(LLM_TIMEOUT))
