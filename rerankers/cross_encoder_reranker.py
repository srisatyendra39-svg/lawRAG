from __future__ import annotations

import time
from functools import lru_cache
from typing import Dict, List, Sequence, Union

import numpy as np
from sentence_transformers import CrossEncoder
from tenacity import retry, stop_after_attempt, wait_fixed

from models.response_models import SearchResult
from utils.logger import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Cross-encoder reranker for refining retrieval candidates."""

    def __init__(self, model_name: str, device: str = "cpu", top_k: int = 5) -> None:
        self.model_name = model_name
        self.device = device
        self.top_k = top_k
        self.model = CrossEncoder(model_name, device=device)

    def warmup(self) -> None:
        """Warm up the reranker with a dummy query-document pair."""
        self.rerank("Warmup query", [SearchResult(chunk_id="warmup", content="Warm up the reranker.", score=0.0, metadata={"act_name":"Unknown","section_number":"","article_number":"","chapter":"","page_number":1,"source_file":""}, rank=1)])

    def rerank(self, query: str, candidates: List[SearchResult]) -> List[SearchResult]:
        """Rerank candidate documents using a cross-encoder."""
        if not candidates:
            return []
        pairs = self._prepare_pairs(query, candidates)
        try:
            scores = self.model.predict(pairs)
        except Exception as exc:
            logger.warning("Cross-encoder rerank failed; returning original candidate order", error=str(exc))
            return candidates

        if isinstance(scores, (float, int, np.floating, np.integer)):
            scores = [float(scores)]
        elif isinstance(scores, np.ndarray):
            scores = scores.tolist()

        reranked: List[SearchResult] = []
        for result, score in sorted(zip(candidates, scores), key=lambda item: item[1], reverse=True):
            reranked.append(
                SearchResult(
                    chunk_id=result.chunk_id,
                    content=result.content,
                    score=float(score),
                    metadata=result.metadata,
                    rank=result.rank,
                    retrieval_method="reranked",
                )
            )
        return reranked[: self.top_k]

    def _prepare_pairs(self, query: str, candidates: List[SearchResult]) -> List[List[str]]:
        """Prepare input pairs for cross-encoder scoring.

        CrossEncoder.predict() expects a list of [query, document] pairs.
        Feed all candidates (up to top_k*3) with longer excerpts for better accuracy.
        """
        pairs: List[List[str]] = []
        for candidate in candidates[: self.top_k * 3]:
            excerpt = candidate.content[:768]
            pairs.append([query, excerpt])
        return pairs

    def get_model_info(self) -> Dict[str, str]:
        """Return reranker model metadata."""
        return {"model_name": self.model_name, "device": self.device}


@lru_cache(maxsize=1)
def get_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = "cpu") -> CrossEncoderReranker:
    """Return a singleton CrossEncoderReranker instance."""
    reranker = CrossEncoderReranker(model_name=model_name, device=device)
    reranker.warmup()
    return reranker
