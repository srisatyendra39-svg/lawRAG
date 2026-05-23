from __future__ import annotations

from generators.ollama_client import OllamaClient
from prompts.query_prompts import build_rewrite_prompt
from utils.logger import get_logger

logger = get_logger(__name__)


class QueryRewriter:
    """Rewrite user questions to be more precise for legal retrieval."""

    def __init__(self, ollama_client: OllamaClient) -> None:
        self.ollama_client = ollama_client

    def rewrite(self, query: str) -> str:
        """Rewrite the provided query using Ollama."""
        prompt = build_rewrite_prompt(query)
        messages = [
            {"role": "user", "content": prompt},
        ]
        try:
            rewritten = self.ollama_client.chat(messages=messages, temperature=0.1, max_tokens=100)
            logger.info("Query rewritten", original=query, rewritten=rewritten)
            return rewritten.strip()
        except Exception as exc:
            logger.error("Query rewrite failed, falling back to original query", error=str(exc))
            return query

