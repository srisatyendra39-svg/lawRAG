from __future__ import annotations

from typing import Dict, List, Optional


from models.response_models import SearchResult
from vectorstore.chroma_store import LegalVectorStore
from utils.logger import get_logger
from utils.text_processing import deduplicate_results

logger = get_logger(__name__)


class SemanticRetriever:
    """Semantic retrieval wrapper around the ChromaDB vector store."""

    def __init__(self, vector_store: LegalVectorStore) -> None:
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        act_filter: Optional[str] = None,
        chapter_filter: Optional[str] = None,
        section_filter: Optional[str] = None,
        kb_id: Optional[str] = "global",
        search_scope: str = "global",
    ) -> List[SearchResult]:
        """Run a semantic search with optional metadata and scope filters."""
        filter_dict = self._build_filter(
            act_filter=act_filter,
            chapter_filter=chapter_filter,
            section_filter=section_filter,
            kb_id=kb_id,
            search_scope=search_scope,
        )
        # Retrieve slightly more than top_k to account for deduplication filtering
        results = self.vector_store.similarity_search(query=query, top_k=top_k * 2, filter_dict=filter_dict)
        sorted_results = sorted(results, key=lambda item: item.score, reverse=True)
        deduped = deduplicate_results(sorted_results)
        return deduped[:top_k]

    def retrieve_by_metadata(
        self,
        act_name: str,
        chapter: Optional[str] = None,
        section: Optional[str] = None,
        kb_id: str = "global",
    ) -> List[SearchResult]:
        """Retrieve chunks using only metadata filters."""
        filter_dict: Dict[str, Any] = {"act_name": act_name, "kb_id": kb_id}
        if chapter:
            filter_dict["chapter"] = chapter
        if section:
            filter_dict["section_number"] = section
        return self.vector_store.get_by_metadata(filter_dict=filter_dict, limit=100)

    def _build_filter(
        self,
        act_filter: Optional[str],
        chapter_filter: Optional[str],
        section_filter: Optional[str],
        kb_id: Optional[str] = "global",
        search_scope: str = "global",
    ) -> Optional[Dict[str, Any]]:
        """Build a ChromaDB filter dictionary from optional metadata and scope values."""
        target_kb = kb_id or "global"
        if search_scope == "global" or target_kb == "global":
            scope_filter = {"kb_id": "global"}
        elif search_scope == "custom":
            scope_filter = {"kb_id": target_kb}
        elif search_scope == "combined":
            scope_filter = {"$or": [{"kb_id": "global"}, {"kb_id": target_kb}]}
        else:
            scope_filter = {"kb_id": "global"}

        filters: List[Dict[str, Any]] = [scope_filter]
        if act_filter:
            filters.append({"act_name": act_filter})
        if chapter_filter:
            filters.append({"chapter": chapter_filter})
        if section_filter:
            filters.append({"section_number": section_filter})

        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}



_semantic_retriever_instance: SemanticRetriever | None = None


def get_semantic_retriever(vector_store: LegalVectorStore) -> SemanticRetriever:
    """Return a singleton SemanticRetriever instance."""
    global _semantic_retriever_instance
    if _semantic_retriever_instance is None:
        _semantic_retriever_instance = SemanticRetriever(vector_store=vector_store)
    return _semantic_retriever_instance
