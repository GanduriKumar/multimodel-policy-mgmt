"""
LLMGateway abstraction with multiple providers (Ollama, OpenAI).

Contract
--------
- LLMClient Protocol with generate(prompt: str, context: dict | None = None) -> str
- OllamaLLMClient: local server over HTTP
- OpenAiLLMClient: OpenAI Chat Completions over HTTP
- create_llm_client(provider: str | None = None) -> LLMClient

Configuration
-------------
Read via app.core.config.get_settings() with environment fallbacks:
- DEFAULT_LLM_PROVIDER (default: "ollama")

Ollama:
- settings.ollama_base_url or env OLLAMA_BASE_URL (default: http://localhost:11434)
- settings.ollama_model or env OLLAMA_MODEL (default: llama3.1)

OpenAI:
- settings.openai_api_key or env OPENAI_API_KEY (required)
- settings.openai_model or env OPENAI_MODEL (default: gpt-4o-mini)

Security & Errors
-----------------
- All HTTP/JSON/connectivity errors raise LLMGatewayError.
- Secrets (API keys) are never logged or included in error messages.
"""

from __future__ import annotations

import enum
import os
from typing import Any, Optional, Protocol, runtime_checkable

from app.core.config import get_settings


class LLMGatewayError(Exception):
    """Raised for downstream LLM gateway errors (HTTP/JSON/connectivity)."""


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, prompt: str, context: Optional[dict] = None) -> str:  # pragma: no cover - protocol
        """Generate a completion for the prompt."""


class LLMProvider(str, enum.Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    VERTEX = "vertex"  # placeholder; not implemented in this module


class OllamaLLMClient:
    """LLMClient implementation for a local Ollama server using httpx.

    Endpoint: POST {base_url}/api/generate
    Payload: {"model": <model>, "prompt": <prompt>, "stream": false, ...}
    Response JSON: {"response": "..."}
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (
            base_url
            or getattr(settings, "ollama_base_url", None)
            or os.getenv("OLLAMA_BASE_URL")
            or "http://localhost:11434"
        ).rstrip("/")
        self.model = (
            model
            or getattr(settings, "ollama_model", None)
            or os.getenv("OLLAMA_MODEL")
            or "llama3.1"
        )
        self.timeout = float(timeout)

    def generate(self, prompt: str, context: Optional[dict] = None) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if isinstance(context, dict):
            opts = context.get("options")
            if isinstance(opts, dict):
                payload["options"] = opts

        try:  # pragma: no cover - import behavior
            import httpx  # type: ignore
        except Exception as e:  # pragma: no cover
            raise LLMGatewayError("httpx is required for OllamaLLMClient. Install with: pip install httpx") from e

        url = f"{self.base_url}/api/generate"
        try:
            with httpx.Client(timeout=self.timeout) as client:  # type: ignore[name-defined]
                resp = client.post(url, json=payload)
        except httpx.RequestError as e:  # type: ignore[name-defined]
            raise LLMGatewayError(f"Failed to reach Ollama at {self.base_url}: {e.__class__.__name__}") from e

        if resp.status_code != 200:
            body_snippet = (resp.text or "")[:200]
            raise LLMGatewayError(f"Ollama HTTP {resp.status_code}: {body_snippet}")

        try:
            data = resp.json()
        except ValueError as e:
            raise LLMGatewayError("Invalid JSON from Ollama") from e

        text = data.get("response")
        if not isinstance(text, str):
            raise LLMGatewayError("Unexpected Ollama response shape: 'response' missing or not a string")
        return text


class OpenAiLLMClient:
    """LLMClient for OpenAI Chat Completions (non-streaming)."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,  # allow overriding base URL for Azure-compatible gateways
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMGatewayError("OPENAI_API_KEY missing; set in settings or environment")
        self.model = model or getattr(settings, "openai_model", None) or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        # Default OpenAI public endpoint; can be replaced for Azure OpenAI with matching schema
        self.base_url = (base_url or getattr(settings, "openai_base_url", None) or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.timeout = float(timeout)

    def generate(self, prompt: str, context: Optional[dict] = None) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        if isinstance(context, dict):
            # allow override of generation options
            if "temperature" in context:
                try:
                    payload["temperature"] = float(context["temperature"])  # type: ignore[assignment]
                except Exception:
                    payload["temperature"] = 0

        try:  # pragma: no cover - import behavior
            import httpx  # type: ignore
        except Exception as e:  # pragma: no cover
            raise LLMGatewayError("httpx is required for OpenAiLLMClient. Install with: pip install httpx") from e

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:  # type: ignore[name-defined]
                resp = client.post(url, headers=headers, json=payload)
        except httpx.RequestError as e:  # type: ignore[name-defined]
            raise LLMGatewayError("Failed to reach OpenAI endpoint") from e

        if resp.status_code != 200:
            body_snippet = (resp.text or "")[:200]
            raise LLMGatewayError(f"OpenAI HTTP {resp.status_code}: {body_snippet}")

        try:
            data = resp.json()
        except ValueError as e:
            raise LLMGatewayError("Invalid JSON from OpenAI") from e

        try:
            choices = data.get("choices") or []
            text = choices[0]["message"]["content"] if choices else ""
        except Exception as e:
            raise LLMGatewayError("Unexpected OpenAI response shape") from e

        if not isinstance(text, str):
            raise LLMGatewayError("Unexpected OpenAI response content type")
        return text


def create_llm_client(provider: Optional[str] = None) -> LLMClient:  # type: ignore[valid-type]
    """Factory that returns an LLMClient based on provider name.

    Args:
        provider: one of {"ollama", "openai", "vertex"}; if None, read from settings.DEFAULT_LLM_PROVIDER
    """
    settings = get_settings()
    name = (provider or getattr(settings, "DEFAULT_LLM_PROVIDER", None) or os.getenv("DEFAULT_LLM_PROVIDER") or LLMProvider.OLLAMA.value).lower()
    if name == LLMProvider.OLLAMA.value:
        return OllamaLLMClient()
    if name == LLMProvider.OPENAI.value:
        return OpenAiLLMClient()
    if name == LLMProvider.VERTEX.value:
        raise LLMGatewayError("Vertex provider not implemented in this build")
    raise LLMGatewayError(f"Unknown LLM provider: {name}")


__all__ = [
    "LLMClient",
    "LLMGatewayError",
    "LLMProvider",
    "OllamaLLMClient",
    "OpenAiLLMClient",
    "create_llm_client",
]

