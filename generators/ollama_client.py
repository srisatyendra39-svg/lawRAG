from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional
import httpx

from utils.logger import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Centralized, connection-pooled client for local Ollama APIs."""

    def __init__(
        self,
        base_url: str,
        model: str,
        client: Optional[httpx.Client] = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        # Reuse external client (for connection pooling) or build a dedicated one
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self._owns_client = client is None

    def is_healthy(self) -> bool:
        """Check if the Ollama service is reachable and responsive."""
        try:
            # The root endpoint or /api/tags can be used for health check
            response = self.client.get(self.base_url, timeout=5.0)
            return response.status_code == 200
        except Exception as exc:
            logger.warning("Ollama health check failed", error=str(exc))
            return False

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """Send a chat request to Ollama and return the full response content."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        url = f"{self.base_url}/api/chat"
        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            if isinstance(message, dict):
                return message.get("content", "").strip()
            return str(data).strip()
        except Exception as exc:
            logger.error("Ollama chat request failed", error=str(exc))
            raise

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> Generator[str, None, str]:
        """Stream chat tokens from Ollama.

        Yields:
            str: Each text chunk/token as it arrives.

        Returns:
            str: The full accumulated text content.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        url = f"{self.base_url}/api/chat"
        full_response: List[str] = []

        try:
            with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        full_response.append(content)
                        yield content
        except Exception as exc:
            logger.error("Ollama streaming request failed", error=str(exc))
            yield f"\n[Error generating response: {exc}]\n"

        return "".join(full_response)

    def close(self) -> None:
        """Close the underlying client if we own it."""
        if self._owns_client and self.client:
            self.client.close()
            logger.info("OllamaClient HTTP pool closed")
