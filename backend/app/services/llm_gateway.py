"""
LLMGateway abstraction and an Ollama-backed client using httpx.

Contract
--------
- LLMClient Protocol with generate(prompt: str, context: dict | None = None) -> str
- OllamaLLMClient: calls a local Ollama server via HTTP (no streaming) and returns the generated text.

Configuration
-------------
Reads from app.core.config.get_settings() with environment fallbacks:
- settings.ollama_base_url or env OLLAMA_BASE_URL (default: http://localhost:11434)
- settings.ollama_model or env OLLAMA_MODEL (default: llama3.1)

Error Handling
--------------
Raises LLMGatewayError on HTTP, connection, or JSON errors. Error messages avoid leaking secrets.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Protocol, runtime_checkable

from app.core.config import get_settings


class LLMGatewayError(Exception):
    """Raised for downstream LLM gateway errors (HTTP/JSON/connectivity)."""


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, prompt: str, context: Optional[dict] = None) -> str:  # pragma: no cover - protocol
        """Generate a completion for the prompt. Must be deterministic for a given prompt/context."""


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
        # Use settings if present, fall back to env, then defaults
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
        # Optionally surface deterministic options from context (e.g., temperature=0)
        if isinstance(context, dict):
            opts = context.get("options")
            if isinstance(opts, dict):
                payload["options"] = opts

        # Lazy import to avoid hard dependency when not used
        try:  # pragma: no cover - import behavior
            import httpx  # type: ignore
        except Exception as e:  # pragma: no cover
            raise LLMGatewayError("httpx is required for OllamaLLMClient. Install with: pip install httpx") from e

        url = f"{self.base_url}/api/generate"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
        except httpx.RequestError as e:  # type: ignore[name-defined]
            # Avoid leaking any sensitive headers or payloads
            raise LLMGatewayError(f"Failed to reach Ollama at {self.base_url}: {e.__class__.__name__}") from e

        if resp.status_code != 200:
            # Trim body to avoid excessive logs; do not include auth headers
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


__all__ = ["LLMClient", "OllamaLLMClient", "LLMGatewayError"]
