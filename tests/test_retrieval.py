from dataclasses import dataclass
from typing import List

import pytest

from chunking.legal_chunker import LegalChunk
from models.response_models import ChunkMetadata, SearchResult
from retrievers.bm25_retriever import BM25Retriever
from retrievers.hybrid_retriever import HybridRetriever
from retrievers.semantic_retriever import SemanticRetriever


class DummySemanticRetriever(SemanticRetriever):
    def __init__(self, results: List[SearchResult]) -> None:
        self._results = results

    def retrieve(self, *args, **kwargs) -> List[SearchResult]:
        return self._results


class DummyBM25Retriever(BM25Retriever):
    def __init__(self, results: List[SearchResult]) -> None:
        super().__init__()
        self._results = results

    def retrieve(self, *args, **kwargs) -> List[SearchResult]:
        return self._results


def build_chunk(chunk_id: str, content: str, score: float, rank: int) -> SearchResult:
    metadata = ChunkMetadata(
        act_name="Information Technology Act, 2000",
        section_number="Section 43",
        article_number="",
        chapter="Chapter IX",
        page_number=10,
        source_file="IT_Act_2000.pdf",
    )
    return SearchResult(chunk_id=chunk_id, content=content, score=score, metadata=metadata, rank=rank)


def test_build_index_with_chunks() -> None:
    retriever = BM25Retriever()
    chunks = [
        LegalChunk(chunk_id="1", content="A", raw_content="A", metadata=ChunkMetadata(act_name="IT Act", section_number="Section 43", article_number="", chapter="", page_number=1, source_file="sample.pdf"), char_count=1, word_count=1),
        LegalChunk(chunk_id="2", content="B", raw_content="B", metadata=ChunkMetadata(act_name="IT Act", section_number="Section 44", article_number="", chapter="", page_number=2, source_file="sample.pdf"), char_count=1, word_count=1),
    ]
    retriever.build_index(chunks)
    assert retriever._index is not None


def test_retrieve_returns_top_k() -> None:
    retriever = BM25Retriever()
    chunks = [
        LegalChunk(chunk_id="1", content="section 43 legal text", raw_content="section 43 legal text", metadata=ChunkMetadata(act_name="IT Act", section_number="Section 43", article_number="", chapter="", page_number=1, source_file="sample.pdf"), char_count=1, word_count=1),
        LegalChunk(chunk_id="2", content="section 44 legal text", raw_content="section 44 legal text", metadata=ChunkMetadata(act_name="IT Act", section_number="Section 44", article_number="", chapter="", page_number=2, source_file="sample.pdf"), char_count=1, word_count=1),
    ]
    retriever.build_index(chunks)
    results = retriever.retrieve("Section 43", top_k=1)
    assert len(results) == 1


def test_section_number_exact_match() -> None:
    retriever = BM25Retriever()
    chunks = [
        LegalChunk(chunk_id="1", content="Section 43A is important.", raw_content="Section 43A is important.", metadata=ChunkMetadata(act_name="IT Act", section_number="Section 43A", article_number="", chapter="", page_number=1, source_file="sample.pdf"), char_count=1, word_count=1),
    ]
    retriever.build_index(chunks)
    results = retriever.retrieve("Section 43A", top_k=1)
    assert results[0].metadata.section_number == "Section 43A"


def test_normalize_scores_range() -> None:
    retriever = BM25Retriever()
    scores = retriever._normalize_scores(__import__("numpy").array([1.0, 2.0, 3.0]))
    assert float(scores.min()) == 0.0
    assert float(scores.max()) == 1.0


def test_hybrid_returns_union_of_results() -> None:
    semantic_results = [build_chunk("1", "semantic", 0.9, 1)]
    bm25_results = [build_chunk("2", "bm25", 0.8, 1)]
    hybrid = HybridRetriever(
        semantic_retriever=DummySemanticRetriever(semantic_results),
        bm25_retriever=DummyBM25Retriever(bm25_results),
    )
    results = hybrid.retrieve("query", top_k=2)
    assert len(results) == 2


def test_rrf_fusion_deduplicates() -> None:
    semantic_results = [build_chunk("1", "semantic", 0.9, 1)]
    bm25_results = [build_chunk("1", "bm25", 0.8, 1)]
    hybrid = HybridRetriever(
        semantic_retriever=DummySemanticRetriever(semantic_results),
        bm25_retriever=DummyBM25Retriever(bm25_results),
    )
    results = hybrid.retrieve("query", top_k=1)
    assert len(results) == 1


def test_alpha_weighting() -> None:
    semantic_results = [build_chunk("1", "semantic", 0.9, 1)]
    bm25_results = [build_chunk("2", "bm25", 0.8, 1)]
    hybrid = HybridRetriever(
        semantic_retriever=DummySemanticRetriever(semantic_results),
        bm25_retriever=DummyBM25Retriever(bm25_results),
        alpha=0.8,
    )
    results = hybrid.retrieve("query", top_k=2)
    assert any(result.chunk_id == "1" for result in results)


def test_fallback_answer_generator_formatting() -> None:
    from unittest.mock import MagicMock
    from generators.answer_generator import LegalAnswerGenerator
    from generators.ollama_client import OllamaClient

    # Mock OllamaClient to raise an exception, triggering the offline fallback
    ollama_mock = MagicMock(spec=OllamaClient)
    ollama_mock.model = "test-model"
    ollama_mock.chat.side_effect = Exception("Ollama is offline")
    ollama_mock.chat_stream.side_effect = Exception("Ollama is offline")

    generator = LegalAnswerGenerator(ollama_client=ollama_mock)
    
    # 1. Empty context case
    res_empty = generator.generate(question="What is section 43?", context="")
    assert "LLM generation is currently unavailable" in res_empty.answer
    assert "No relevant legal context" in res_empty.answer

    # 2. Context case with beautiful headers
    context = (
        "Source [1] | Information Technology Act, 2000 | Section 43A | Relevance: 0.850\n"
        "Section 43A: Compensation for failure to protect data. Where a body corporate...\n"
        "---"
    )
    res_context = generator.generate(question="What is section 43A?", context=context)
    assert "LLM generation is currently unavailable" in res_context.answer
    assert "### 📜 Section 43A — Information Technology Act, 2000" in res_context.answer
    assert "Relevance: 0.850" in res_context.answer
    assert "Where a body corporate" in res_context.answer
