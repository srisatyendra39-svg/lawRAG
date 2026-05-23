from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from chunking.legal_chunker import LegalChunk
from models.response_models import SearchResult
from utils.logger import get_logger


logger = get_logger(__name__)


class BM25Retriever:
    """BM25 keyword retriever for legal document chunks partitioned by kb_id."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._kb_chunks: Dict[str, List[LegalChunk]] = {}
        self._kb_indices: Dict[str, BM25Okapi] = {}
        self._stopwords = self._load_stopwords()

    @property
    def _chunks(self) -> List[LegalChunk]:
        return self._kb_chunks.get("global", [])

    @_chunks.setter
    def _chunks(self, val: List[LegalChunk]) -> None:
        self._kb_chunks["global"] = val

    @property
    def _index(self) -> Optional[BM25Okapi]:
        return self._kb_indices.get("global")

    @_index.setter
    def _index(self, val: Optional[BM25Okapi]) -> None:
        if val is not None:
            self._kb_indices["global"] = val

    def _load_stopwords(self) -> set[str]:
        try:
            return set(stopwords.words("english"))
        except LookupError:
            import nltk

            nltk.download("stopwords", quiet=True)
            return set(stopwords.words("english"))

    def build_index(self, chunks: List[LegalChunk], kb_id: str = "global") -> None:
        """Build BM25 index from legal chunk text content for a specific KB."""
        self._kb_chunks[kb_id] = chunks
        tokenized = [self._tokenize(chunk.raw_content) or ["__empty__"] for chunk in chunks]
        if tokenized and any(len(t) > 0 for t in tokenized):
            self._kb_indices[kb_id] = BM25Okapi(tokenized, k1=self.k1, b=self.b)
        else:
            self._kb_indices.pop(kb_id, None)
        logger.info("BM25 index built", chunk_count=len(chunks), kb_id=kb_id)

    def rebuild_from_vector_store(self, vector_store: Any) -> None:
        """Fetch all documents from ChromaDB, reconstruct LegalChunk objects, and build BM25 indices grouped by kb_id."""
        if not vector_store.collection_exists():
            self._kb_chunks.clear()
            self._kb_indices.clear()
            return

        collection_data = vector_store.collection.get(include=["documents", "metadatas"])
        
        self._kb_chunks.clear()
        self._kb_indices.clear()

        chunks_by_kb: Dict[str, List[LegalChunk]] = {}
        for doc, metadata in zip(collection_data["documents"], collection_data["metadatas"]):
            from chunking.legal_chunker import LegalChunk
            from models.response_models import ChunkMetadata

            kb_id = metadata.get("kb_id", "global")
            chunk = LegalChunk(
                chunk_id="",
                content=doc,
                raw_content=doc,
                metadata=ChunkMetadata(
                    act_name=metadata.get("act_name", ""),
                    section_number=metadata.get("section_number", ""),
                    article_number=metadata.get("article_number", ""),
                    chapter=metadata.get("chapter", ""),
                    page_number=int(metadata.get("page_number", 0)),
                    source_file=metadata.get("source_file", ""),
                    kb_id=kb_id,
                    doc_category=metadata.get("doc_category", "global"),
                ),
                char_count=len(doc),
                word_count=len(doc.split()),
            )
            if kb_id not in chunks_by_kb:
                chunks_by_kb[kb_id] = []
            chunks_by_kb[kb_id].append(chunk)

        for kb_id, kb_chunks in chunks_by_kb.items():
            self.build_index(kb_chunks, kb_id=kb_id)

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        kb_id: Optional[str] = "global",
        search_scope: str = "global",
    ) -> List[SearchResult]:
        """Retrieve top_k BM25 results for the query, filtered by scope and kb_id."""
        target_kb = kb_id or "global"
        
        kbs_to_search: List[str] = []
        if search_scope == "global" or target_kb == "global":
            kbs_to_search = ["global"]
        elif search_scope == "custom":
            kbs_to_search = [target_kb]
        elif search_scope == "combined":
            kbs_to_search = ["global", target_kb]
        else:
            kbs_to_search = ["global"]

        all_results: List[SearchResult] = []
        tokens = self._tokenize(query)
        if not tokens:
            return []

        for kb in kbs_to_search:
            index = self._kb_indices.get(kb)
            chunks = self._kb_chunks.get(kb, [])
            if index is None or not chunks:
                continue
            
            scores = np.array(index.get_scores(tokens), dtype=float)
            normalized = self._normalize_scores(scores)
            
            for i, score in enumerate(normalized):
                chunk = chunks[i]
                all_results.append(
                    SearchResult(
                        chunk_id=chunk.chunk_id or f"bm25_{kb}_{i}",
                        content=chunk.content,
                        score=float(score),
                        metadata=chunk.metadata,
                        rank=1,
                        retrieval_method="bm25",
                    )
                )

        if not all_results:
            return []

        sorted_results = sorted(all_results, key=lambda item: item.score, reverse=True)
        for rank, result in enumerate(sorted_results[:top_k], start=1):
            result.rank = rank
            
        return sorted_results[:top_k]

    def save_index(self, path: Path) -> None:
        """Persist BM25 chunks to disk as JSON (no pickle for security)."""
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        serializable = []
        for kb_id, chunks in self._kb_chunks.items():
            for chunk in chunks:
                serializable.append({
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "raw_content": chunk.raw_content,
                    "metadata": {
                        "act_name": chunk.metadata.act_name,
                        "section_number": chunk.metadata.section_number,
                        "article_number": chunk.metadata.article_number,
                        "chapter": chunk.metadata.chapter,
                        "page_number": chunk.metadata.page_number,
                        "source_file": chunk.metadata.source_file,
                        "kb_id": chunk.metadata.kb_id,
                        "doc_category": chunk.metadata.doc_category,
                    },
                    "char_count": chunk.char_count,
                    "word_count": chunk.word_count,
                })
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(serializable, handle)
        logger.info("BM25 index saved", path=str(path))

    def load_index(self, path: Path) -> None:
        """Load BM25 chunks from JSON and rebuild indices."""
        import json
        from models.response_models import ChunkMetadata

        if not path.exists():
            raise FileNotFoundError(f"BM25 index file not found: {path}")
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        
        self._kb_chunks.clear()
        self._kb_indices.clear()

        chunks_by_kb: Dict[str, List[LegalChunk]] = {}
        for item in data:
            chunk = LegalChunk(
                chunk_id=item["chunk_id"],
                content=item["content"],
                raw_content=item["raw_content"],
                metadata=ChunkMetadata(**item["metadata"]),
                char_count=item["char_count"],
                word_count=item["word_count"],
            )
            kb_id = chunk.metadata.kb_id or "global"
            if kb_id not in chunks_by_kb:
                chunks_by_kb[kb_id] = []
            chunks_by_kb[kb_id].append(chunk)

        for kb_id, kb_chunks in chunks_by_kb.items():
            self.build_index(kb_chunks, kb_id=kb_id)
        logger.info("BM25 index loaded", path=str(path), kb_count=len(self._kb_chunks))

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize legal text into normalized terms with numbers attached."""
        if not text:
            return []
        normalized = text.lower()
        normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
        tokens = word_tokenize(normalized)
        result: List[str] = []
        for token in tokens:
            if token in self._stopwords or len(token) < 2:
                continue
            result.append(token)
            if token.isdigit():
                result.append(token)
        return result

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Scale BM25 scores into the 0-1 range."""
        if scores.size == 0:
            return scores
        min_score = float(np.min(scores))
        max_score = float(np.max(scores))
        if math.isclose(min_score, max_score):
            return np.ones_like(scores)
        return (scores - min_score) / (max_score - min_score)

def get_bm25_retriever() -> BM25Retriever:
    """Return a fresh BM25 retriever instance."""
    return BM25Retriever()
