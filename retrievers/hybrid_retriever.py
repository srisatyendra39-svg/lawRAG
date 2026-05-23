from __future__ import annotations

from typing import Dict, List, Optional

from models.response_models import SearchResult
from retrievers.bm25_retriever import BM25Retriever
from retrievers.semantic_retriever import SemanticRetriever
from utils.logger import get_logger
from utils.text_processing import deduplicate_results

logger = get_logger(__name__)


class HybridRetriever:
    """Hybrid retriever that merges BM25 and semantic retrieval results."""

    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        bm25_retriever: BM25Retriever,
        alpha: float = 0.5,
    ) -> None:
        self.semantic_retriever = semantic_retriever
        self.bm25_retriever = bm25_retriever
        self.alpha = alpha

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        act_filter: Optional[str] = None,
        chapter_filter: Optional[str] = None,
        section_filter: Optional[str] = None,
        kb_id: Optional[str] = "global",
        search_scope: str = "global",
        alpha: Optional[float] = None,
    ) -> List[SearchResult]:
        """Retrieve results from both semantic and BM25 search and fuse them."""
        semantic_results = self.semantic_retriever.retrieve(
            query=query,
            top_k=top_k * 2,
            act_filter=act_filter,
            chapter_filter=chapter_filter,
            section_filter=section_filter,
            kb_id=kb_id,
            search_scope=search_scope,
        )
        bm25_results = self.bm25_retriever.retrieve(
            query=query,
            top_k=top_k * 2,
            kb_id=kb_id,
            search_scope=search_scope,
        )
        
        # Apply metadata filtering to BM25 results
        if act_filter or chapter_filter or section_filter:
            filtered_bm25 = []
            for result in bm25_results:
                if act_filter and result.metadata.act_name != act_filter:
                    continue
                if chapter_filter and result.metadata.chapter != chapter_filter:
                    continue
                if section_filter and result.metadata.section_number != section_filter:
                    continue
                filtered_bm25.append(result)
            bm25_results = filtered_bm25

        fused = self._reciprocal_rank_fusion(semantic_results, bm25_results, alpha=alpha)
        fused_sorted = sorted(fused, key=lambda result: result.score, reverse=True)
        unique_results = self._deduplicate(fused_sorted)
        for rank, result in enumerate(unique_results[:top_k], start=1):
            result.rank = rank
        return unique_results[:top_k]

    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[SearchResult],
        bm25_results: List[SearchResult],
        k: int = 60,
        alpha: Optional[float] = None,
    ) -> List[SearchResult]:
        """Fuse results using Reciprocal Rank Fusion."""
        score_map: Dict[str, float] = {}
        result_map: Dict[str, SearchResult] = {}
        weight_alpha = alpha if alpha is not None else self.alpha

        for rank, result in enumerate(semantic_results, start=1):
            score_map[result.chunk_id] = score_map.get(result.chunk_id, 0.0) + weight_alpha / (rank + k)
            result_map[result.chunk_id] = result

        for rank, result in enumerate(bm25_results, start=1):
            score_map[result.chunk_id] = score_map.get(result.chunk_id, 0.0) + (1.0 - weight_alpha) / (rank + k)
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result

        fused_results: List[SearchResult] = []
        for chunk_id, score in score_map.items():
            base_result = result_map[chunk_id]
            fused = SearchResult(
                chunk_id=base_result.chunk_id,
                content=base_result.content,
                score=score,
                metadata=base_result.metadata,
                rank=base_result.rank,
                retrieval_method="hybrid",
            )
            fused_results.append(fused)
        return fused_results

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """Deduplicate results by chunk_id and content overlap, keeping the highest score."""
        return deduplicate_results(results)


_hybrid_retriever_instance: HybridRetriever | None = None


def get_hybrid_retriever(
    semantic_retriever: SemanticRetriever,
    bm25_retriever: BM25Retriever,
    alpha: float = 0.5,
) -> HybridRetriever:
    """Return a singleton HybridRetriever instance."""
    global _hybrid_retriever_instance
    if _hybrid_retriever_instance is None:
        _hybrid_retriever_instance = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_retriever=bm25_retriever,
            alpha=alpha,
        )
    return _hybrid_retriever_instance
