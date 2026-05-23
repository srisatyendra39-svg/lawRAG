from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import chromadb
from chromadb.config import Settings

from chromadb.utils import embedding_functions
from tenacity import retry, stop_after_attempt, wait_fixed

from models.response_models import ChunkMetadata, SearchResult
from embeddings.embedder import LangChainEmbeddingAdapter
from utils.logger import get_logger


logger = get_logger(__name__)


class LegalVectorStore:
    """ChromaDB-backed vector store for legal chunks."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embedding_service: LangChainEmbeddingAdapter,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedding_service = embedding_service
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
        )
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> chromadb.api.models.Collection:
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception:
            return self.client.create_collection(name=self.collection_name)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def add_chunks(self, chunks: List[Any]) -> int:
        """Add legal chunks to ChromaDB and return the count of inserted chunks."""
        if not chunks:
            return 0

        ids = []
        metadatas = []
        documents = []

        for chunk in chunks:
            ids.append(chunk.chunk_id)
            documents.append(chunk.raw_content)
            metadatas.append({
                "act_name": chunk.metadata.act_name,
                "section_number": chunk.metadata.section_number,
                "article_number": chunk.metadata.article_number,
                "chapter": chunk.metadata.chapter,
                "page_number": chunk.metadata.page_number,
                "source_file": chunk.metadata.source_file,
                "kb_id": getattr(chunk.metadata, "kb_id", "global"),
                "doc_category": getattr(chunk.metadata, "doc_category", "global"),
            })

        # Batch encode all documents
        embeddings = self.embedding_service.embed_documents(documents)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        logger.info("Added chunks to ChromaDB", count=len(ids), collection=self.collection_name)
        return len(ids)

    def similarity_search(
        self,
        query: str,
        top_k: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Perform semantic similarity search and return SearchResult objects."""
        query_embedding = self.embedding_service.embed_query(query)
        query_filter = filter_dict if filter_dict else None
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=query_filter,
            include=['metadatas', 'documents', 'distances'],
        )
        return self._chroma_to_search_results(results)

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return metadata statistics for the collection."""
        total_chunks = len(self.collection.get()['ids'])
        chunks_per_act: Dict[str, int] = {}
        chunks_per_chapter: Dict[str, int] = {}
        metadatas = self.collection.get()['metadatas']
        for metadata in metadatas:
            act_name = metadata.get('act_name', 'Unknown')
            chapter = metadata.get('chapter', 'Unknown')
            chunks_per_act[act_name] = chunks_per_act.get(act_name, 0) + 1
            chunks_per_chapter[chapter] = chunks_per_chapter.get(chapter, 0) + 1
        return {
            'total_chunks': total_chunks,
            'chunks_per_act': chunks_per_act,
            'chunks_per_chapter': chunks_per_chapter,
        }

    def delete_by_act(self, act_name: str) -> int:
        """Delete all chunks from a specific act and return the count removed."""
        if not self.collection_exists():
            return 0
        # Use get() with where filter to find matching IDs (query with n_results=0 returns nothing)
        results = self.collection.get(
            where={"act_name": act_name},
            include=[],
        )
        ids = results.get('ids', [])
        if not ids:
            return 0
        self.collection.delete(ids=ids)
        logger.info("Deleted chunks by act", act_name=act_name, deleted_count=len(ids))
        return len(ids)

    def delete_by_kb(self, kb_id: str) -> int:
        """Delete all chunks from a specific knowledge base."""
        if not self.collection_exists():
            return 0
        results = self.collection.get(
            where={"kb_id": kb_id},
            include=[],
        )
        ids = results.get('ids', [])
        if not ids:
            return 0
        self.collection.delete(ids=ids)
        logger.info("Deleted chunks by kb_id", kb_id=kb_id, deleted_count=len(ids))
        return len(ids)

    def collection_exists(self) -> bool:
        """Return whether the collection exists and has data."""
        try:
            collection = self.client.get_collection(name=self.collection_name)
            return collection.count() > 0
        except Exception:
            return False

    def get_by_metadata(
        self,
        filter_dict: Dict[str, Any],
        limit: int = 100,
    ) -> List[SearchResult]:
        """Retrieve chunks from ChromaDB using only metadata filters (no vector search)."""
        results = self.collection.get(
            where=filter_dict,
            limit=limit,
            include=['metadatas', 'documents'],
        )
        query_results = {
            'ids': [results.get('ids', [])],
            'documents': [results.get('documents', [])],
            'metadatas': [results.get('metadatas', [])],
            'distances': [[0.0] * len(results.get('ids', []))],
        }
        return self._chroma_to_search_results(query_results)

    def reset_collection(self) -> None:
        """Clear all data from the collection."""
        if self.collection_exists():
            self.collection.delete(where={})
            logger.warning("Reset ChromaDB collection", collection=self.collection_name)

    def _chroma_to_search_results(self, results: Dict[str, Any]) -> List[SearchResult]:
        """Convert Chroma query results to SearchResult list."""
        ids = results.get('ids', [[]])[0]
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        search_results: List[SearchResult] = []
        for rank, (chunk_id, doc, metadata, distance) in enumerate(zip(ids, documents, metadatas, distances), start=1):
            score = 1.0 - distance if distance is not None else 0.0
            chunk_metadata = ChunkMetadata(
                act_name=metadata.get('act_name', ''),
                section_number=metadata.get('section_number', ''),
                article_number=metadata.get('article_number', ''),
                chapter=metadata.get('chapter', ''),
                page_number=int(metadata.get('page_number', 0)),
                source_file=metadata.get('source_file', ''),
                kb_id=metadata.get('kb_id', 'global'),
                doc_category=metadata.get('doc_category', 'global'),
            )
            search_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    content=doc,
                    score=score,
                    metadata=chunk_metadata,
                    rank=rank,
                )
            )
        return search_results


@lru_cache(maxsize=1)
def get_vector_store() -> LegalVectorStore:
    """Return a singleton LegalVectorStore instance."""
    from configs.settings import get_settings
    from embeddings.embedder import get_langchain_embedding_adapter

    settings = get_settings()
    return LegalVectorStore(
        persist_dir=str(settings.chroma_persist_dir),
        collection_name=settings.chroma_collection_name,
        embedding_service=get_langchain_embedding_adapter(),
    )
