from __future__ import annotations

from functools import lru_cache
from typing import Any

from loguru import logger as _logger


import sys

import contextvars

correlation_id_var = contextvars.ContextVar("correlation_id", default="none")


class RequestContextFilter:
    """Loguru filter that injects correlation context into logs."""

    def __call__(self, record: dict[str, Any]) -> bool:
        record["extra"]["correlation_id"] = record["extra"].get(
            "correlation_id", correlation_id_var.get("none")
        )
        return True


def _configure_logger() -> None:
    _logger.remove()
    _logger.add(
        sink=sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level> | {extra[correlation_id]}",
        level="DEBUG",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        filter=RequestContextFilter(),
    )


_logger_configured = False


def _ensure_configured() -> None:
    """Configure loguru exactly once."""
    global _logger_configured
    if not _logger_configured:
        _configure_logger()
        _logger_configured = True


def get_logger(name: str) -> _logger.__class__:
    """Return a configured logger for the current module."""
    _ensure_configured()
    return _logger.bind(module=name)


@lru_cache(maxsize=1)
def get_global_logger() -> _logger.__class__:
    """Return the shared singleton logger instance."""
    _ensure_configured()
    return _logger.bind(module="legal_rag")


def log_query(query: str, metadata: dict[str, Any] | None = None) -> None:
    """Log details about a legal query."""
    get_global_logger().info("Query executed", query=query, metadata=metadata or {})


def log_retrieval(source: str, count: int, metadata: dict[str, Any] | None = None) -> None:
    """Log retrieval operations and statistics."""
    get_global_logger().debug(
        "Retrieval completed",
        source=source,
        result_count=count,
        metadata=metadata or {},
    )


def log_generation(question: str, answer_length: int, metadata: dict[str, Any] | None = None) -> None:
    """Log generated answers from the LLM."""
    get_global_logger().info(
        "Answer generated",
        question=question,
        answer_length=answer_length,
        metadata=metadata or {},
    )
