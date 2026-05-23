from __future__ import annotations

import re
import time
from typing import Generator, List, Optional

from generators.ollama_client import OllamaClient
from models.response_models import Citation, RAGResponse
from prompts.query_prompts import build_qa_prompt
from prompts.system_prompts import LEGAL_SYSTEM_PROMPT
from utils.logger import get_logger
from utils.text_processing import clean_repeated_sentences, deduplicate_citations

logger = get_logger(__name__)


class LegalAnswerGenerator:
    """Generate legal answers using Ollama from retrieved context."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> None:
        self.ollama_client = ollama_client
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.model = ollama_client.model

    def generate(
        self,
        question: str,
        context: str,
        rewritten_query: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> RAGResponse:
        """Generate a full legal answer to the question using provided context."""
        prompt = build_qa_prompt(question=question, context=context)
        start = time.perf_counter()
        messages = [
            {"role": "system", "content": LEGAL_SYSTEM_PROMPT.strip()},
            {"role": "user", "content": prompt},
        ]
        
        try:
            answer_text = self.ollama_client.chat(
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            logger.warning("Ollama connection failed; generating offline fallback answer from context", error=str(exc))
            # Synthesize a friendly offline answer using the retrieved context
            answer_text = self._format_fallback_answer(context)

        latency_ms = (time.perf_counter() - start) * 1000
        cleaned_answer = clean_repeated_sentences(answer_text)
        citations = self._extract_citations(cleaned_answer)
        citations = deduplicate_citations(citations)
        response = RAGResponse(
            question=question,
            answer=cleaned_answer.strip(),
            citations=citations,
            rewritten_query=rewritten_query,
            latency_ms=latency_ms,
            model_used=self.model,
        )
        logger.info("Generated legal answer", question=question, latency_ms=latency_ms)
        return response

    def generate_stream(
        self,
        question: str,
        context: str,
        rewritten_query: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, RAGResponse]:
        """Generate answer text in a streaming manner using Ollama's streaming API."""
        prompt = build_qa_prompt(question=question, context=context)
        messages = [
            {"role": "system", "content": LEGAL_SYSTEM_PROMPT.strip()},
            {"role": "user", "content": prompt},
        ]

        start_time = time.perf_counter()
        full_answer = []

        try:
            # chat_stream yields tokens and raises exceptions on failure
            for content in self.ollama_client.chat_stream(
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=self.max_tokens,
            ):
                full_answer.append(content)
                yield content
        except Exception as exc:
            logger.warning("Ollama connection failed; streaming offline fallback answer from context", error=str(exc))
            fallback_msg = self._format_fallback_answer(context)
            full_answer.append(fallback_msg)
            yield fallback_msg

        latency_ms = (time.perf_counter() - start_time) * 1000
        answer_text = "".join(full_answer)
        cleaned_answer = clean_repeated_sentences(answer_text)
        citations = self._extract_citations(cleaned_answer)
        citations = deduplicate_citations(citations)
        
        rag_response = RAGResponse(
            question=question,
            answer=cleaned_answer.strip(),
            citations=citations,
            rewritten_query=rewritten_query,
            latency_ms=latency_ms,
            model_used=self.model,
        )
        return rag_response

    def _format_fallback_answer(self, context: str) -> str:
        """Format the retrieved context cleanly for the fallback response."""
        if not context.strip():
            return (
                f"⚠️ **Note: LLM generation is currently unavailable. Using database fallback mode.**\n\n"
                f"No relevant legal context was retrieved for your query, and the LLM could not be reached."
            )

        # Context blocks are separated by "\n---" as formatted in query_prompts.py
        blocks = context.split("\n---")
        formatted_blocks = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.split("\n")
            if not lines:
                continue
            
            # The first line is the header, e.g., "Source [1] | Act | Section | Relevance: 0.900"
            header = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            
            # Parse header parts
            header_parts = [p.strip() for p in header.split("|")]
            
            source_label = header_parts[0] if len(header_parts) > 0 else "Source"
            act_name = ""
            section_or_article = ""
            relevance = ""
            
            for part in header_parts[1:]:
                if "Relevance:" in part:
                    relevance = part
                elif "Section" in part:
                    section_or_article = part
                elif "Article" in part:
                    section_or_article = part
                elif part.startswith("Source ["):
                    continue
                elif "Chapter" in part or "Page" in part:
                    continue
                else:
                    # Treat the first non-metadata part as Act name
                    if not act_name:
                        act_name = part

            title_parts = []
            if section_or_article:
                title_parts.append(section_or_article)
            if act_name:
                title_parts.append(act_name)
            
            title = " — ".join(title_parts)
            if not title:
                title = source_label
                
            formatted_block = f"### 📜 {title}\n"
            if relevance:
                formatted_block += f"*{relevance}*\n\n"
            else:
                formatted_block += "\n"
                
            formatted_block += f"{content}\n"
            formatted_blocks.append(formatted_block)

        bullets = "\n\n".join(formatted_blocks)
        return (
            f"⚠️ **Note: LLM generation is currently unavailable. Using database fallback mode.**\n\n"
            f"Here is the retrieved legal context from the database for your query:\n\n"
            f"{bullets}"
        )

    def _extract_citations(self, answer: str) -> List[Citation]:
        """Extract citations from the generated answer text."""
        citations: List[Citation] = []
        pattern = re.compile(
            r"\[([^\]]+?)\s*-\s*Section\s*([^,\]]+)?(?:,?\s*Page\s*(\d+))?\]|\[([^\]]+?)\s*-\s*Article\s*([^,\]]+)?(?:,?\s*Page\s*(\d+))?\]",
            re.IGNORECASE,
        )
        for match in pattern.finditer(answer):
            act_name = match.group(1) or match.group(4) or ""
            section = match.group(2) or ""
            article = match.group(5) or ""
            page = int(match.group(3) or match.group(6) or 0)
            citations.append(
                Citation(
                    act_name=act_name.strip(),
                    section=section.strip(),
                    article=article.strip(),
                    chapter="",
                    page=page,
                    quote="",
                )
            )
        return citations
