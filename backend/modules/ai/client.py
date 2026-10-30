"""
Minimal Ollama HTTP client (https://github.com/ollama/ollama/blob/main/docs/api.md).
No SDK dependency; uses httpx.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.core.config import get_settings

logger = logging.getLogger("ai.ollama")


class AIUnavailable(RuntimeError):
    """Ollama is disabled, unreachable, or the model is missing."""


class ToolsNotSupported(RuntimeError):
    """The configured model cannot do function calling."""


class OllamaClient:
    def __init__(self) -> None:
        s = get_settings()
        self.enabled = s.AI_ENABLED
        self.base_url = s.OLLAMA_URL.rstrip("/")
        self.model = s.OLLAMA_MODEL
        self.timeout = s.OLLAMA_TIMEOUT_SECONDS

    def status(self) -> dict[str, Any]:
        info = {"enabled": self.enabled, "model": self.model, "reachable": False, "model_available": False}
        if not self.enabled:
            return info
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            info["reachable"] = True
            names = {m.get("name", "") for m in r.json().get("models", [])}
            info["model_available"] = self.model in names or f"{self.model}:latest" in names
        except httpx.HTTPError as e:
            info["error"] = str(e)
        return info

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Returns Ollama's assistant `message` dict ({role, content, tool_calls?})."""
        if not self.enabled:
            raise AIUnavailable("AI features are disabled (AI_ENABLED=false).")

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            # Larger context so tool results fit; small models default to 2-4k tokens.
            "options": {"temperature": temperature, "num_ctx": 8192},
        }
        if tools:
            body["tools"] = tools

        try:
            r = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
        except httpx.TimeoutException as e:
            raise AIUnavailable(f"The AI model took longer than {self.timeout}s to answer.") from e
        except httpx.HTTPError as e:
            raise AIUnavailable(f"Cannot reach Ollama at {self.base_url}: {e}") from e

        if r.status_code == 404:
            raise AIUnavailable(f"Model '{self.model}' is not installed. Run: ollama pull {self.model}")
        if r.status_code >= 400:
            detail = r.text
            try:
                detail = r.json().get("error", detail)
            except ValueError:
                pass
            if "does not support tools" in detail:
                raise ToolsNotSupported(detail)
            raise AIUnavailable(f"Ollama error {r.status_code}: {detail}")

        return r.json().get("message") or {"role": "assistant", "content": ""}
