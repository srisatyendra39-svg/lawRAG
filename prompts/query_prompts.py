from __future__ import annotations

from typing import List

from models.response_models import SearchResult
from prompts.system_prompts import LEGAL_QA_PROMPT, QUERY_REWRITE_PROMPT


def format_context(results: List[SearchResult]) -> str:
    """Format retrieval results into a structured legal context block.

    Each passage is clearly numbered and tagged with metadata so the LLM
    can precisely attribute claims to specific sources.
    """
    lines: List[str] = []
    for index, result in enumerate(results, start=1):
        meta = result.metadata
        # Build a rich header with all available metadata
        header_parts = [f"Source [{index}]"]
        if meta.act_name:
            header_parts.append(meta.act_name)
        if meta.chapter:
            header_parts.append(meta.chapter)
        if meta.section_number:
            header_parts.append(meta.section_number)
        if meta.article_number:
            header_parts.append(meta.article_number)
        if meta.page_number and meta.page_number > 0:
            header_parts.append(f"Page {meta.page_number}")
        header_parts.append(f"Relevance: {result.score:.3f}")

        lines.append(" | ".join(header_parts))
        lines.append(result.content.strip())
        lines.append("---")
    return "\n".join(lines).strip()


def build_qa_prompt(question: str, context: str) -> str:
    """Build the final prompt for legal QA generation."""
    return LEGAL_QA_PROMPT.format(question=question, context=context)


def build_rewrite_prompt(query: str) -> str:
    """Build the prompt to rewrite a user question."""
    return QUERY_REWRITE_PROMPT.format(query=query)
