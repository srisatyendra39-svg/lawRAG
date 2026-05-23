from __future__ import annotations

from functools import lru_cache
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from configs.settings import Settings, get_settings
from embeddings.embedder import EmbeddingService, get_embedding_service
from ingestion.pipeline import IngestionPipeline
from retrievers.bm25_retriever import BM25Retriever, get_bm25_retriever
from retrievers.hybrid_retriever import HybridRetriever, get_hybrid_retriever
from retrievers.semantic_retriever import SemanticRetriever, get_semantic_retriever
from rerankers.cross_encoder_reranker import CrossEncoderReranker, get_reranker
from generators.ollama_client import OllamaClient
from generators.answer_generator import LegalAnswerGenerator
from generators.query_rewriter import QueryRewriter
from vectorstore.chroma_store import LegalVectorStore, get_vector_store


@lru_cache(maxsize=1)
def get_settings_dependency() -> Settings:
    """Return the cached application settings."""
    return get_settings()


@lru_cache(maxsize=1)
def get_embedding_service_dependency() -> EmbeddingService:
    """Return the shared embedding service."""
    return get_embedding_service()


@lru_cache(maxsize=1)
def get_vector_store_dependency() -> LegalVectorStore:
    """Return the shared ChromaDB vector store."""
    return get_vector_store()


@lru_cache(maxsize=1)
def get_bm25_retriever_dependency() -> BM25Retriever:
    """Return the shared BM25 retriever."""
    return get_bm25_retriever()


@lru_cache(maxsize=1)
def get_semantic_retriever_dependency() -> SemanticRetriever:
    """Return the shared semantic retriever."""
    return get_semantic_retriever(get_vector_store_dependency())


@lru_cache(maxsize=1)
def get_hybrid_retriever_dependency() -> HybridRetriever:
    """Return the shared hybrid retriever."""
    settings = get_settings_dependency()
    return get_hybrid_retriever(
        semantic_retriever=get_semantic_retriever_dependency(),
        bm25_retriever=get_bm25_retriever_dependency(),
        alpha=settings.hybrid_alpha,
    )


@lru_cache(maxsize=1)
def get_reranker_dependency() -> CrossEncoderReranker:
    """Return the shared cross-encoder reranker."""
    settings = get_settings_dependency()
    return get_reranker(model_name=settings.reranker_model, device=settings.embedding_device)


@lru_cache(maxsize=1)
def get_ollama_client_dependency() -> OllamaClient:
    """Return the shared connection-pooled OllamaClient."""
    settings = get_settings_dependency()
    return OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=180.0,
    )


@lru_cache(maxsize=1)
def get_query_rewriter_dependency() -> QueryRewriter:
    """Return the shared query rewriter service."""
    return QueryRewriter(ollama_client=get_ollama_client_dependency())


@lru_cache(maxsize=1)
def get_answer_generator_dependency() -> LegalAnswerGenerator:
    """Return the shared answer generator service."""
    settings = get_settings_dependency()
    return LegalAnswerGenerator(
        ollama_client=get_ollama_client_dependency(),
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )


@lru_cache(maxsize=1)
def get_ingestion_pipeline_dependency() -> IngestionPipeline:
    """Return the shared ingestion pipeline."""
    from ingestion.metadata_extractor import LegalMetadataExtractor
    from ingestion.pdf_loader import PDFLoader
    from ingestion.document_parser import DocumentParser
    from chunking.legal_chunker import LegalChunker

    settings = get_settings_dependency()
    return IngestionPipeline(
        document_parser=DocumentParser(pdf_loader=PDFLoader()),
        metadata_extractor=LegalMetadataExtractor(act_mappings=settings.act_mappings),
        chunker=LegalChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ),
        vector_store=get_vector_store_dependency(),
        act_mappings=settings.act_mappings,
    )


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(
    api_key_header_val: Optional[str] = Security(api_key_header),
    settings: Settings = Depends(get_settings_dependency),
) -> Optional[str]:
    """Verify the request's API key matches the configured value if API_KEY is set."""
    if settings.api_key:
        if not api_key_header_val or api_key_header_val != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API Key",
            )
    return api_key_header_val
