from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

# Mock modules that load expensive ML models or libraries
st_mock = MagicMock()
sys.modules["sentence_transformers"] = st_mock

st_util_mock = MagicMock()
sys.modules["sentence_transformers.util"] = st_util_mock


from models.response_models import ChunkMetadata, SearchResult



# ── Define Mock Classes ──────────────────────────────────────────

class MockEmbeddingService:
    def warmup(self) -> None:
        pass

    def embed_query(self, query: str) -> list[float]:
        return [0.1] * 768

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in documents]


class MockVectorStore:
    def collection_exists(self) -> bool:
        return True

    def get_collection_stats(self) -> dict[str, int]:
        return {
            "total_chunks": 42,
            "chunks_per_act": {"Information Technology Act, 2000": 42},
        }

    def add_chunks(self, chunks: list[Any]) -> int:
        return len(chunks)

    def similarity_search(self, query: str, top_k: int = 5, filter_dict: dict | None = None) -> list[SearchResult]:
        return [
            SearchResult(
                chunk_id="test-1",
                content="Mocked similarity search content",
                score=0.95,
                metadata=ChunkMetadata(
                    act_name="Information Technology Act, 2000",
                    section_number="Section 43A",
                    article_number="",
                    chapter="",
                    page_number=12,
                    source_file="it_act.pdf"
                ),
                rank=1
            )
        ]

    def get_by_metadata(self, filter_dict: dict, limit: int = 100) -> list[SearchResult]:
        return [
            SearchResult(
                chunk_id="test-2",
                content="Mocked metadata search content",
                score=1.0,
                metadata=ChunkMetadata(
                    act_name="Information Technology Act, 2000",
                    section_number="Section 43A",
                    article_number="",
                    chapter="",
                    page_number=12,
                    source_file="it_act.pdf"
                ),
                rank=1
            )
        ]

    def delete_by_act(self, act_name: str) -> int:
        return 5

    def delete_by_kb(self, kb_id: str) -> int:
        return 5


class MockReranker:
    def warmup(self) -> None:
        pass

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        return results


class MockOllamaClient:
    def __init__(self, model: str = "llama3") -> None:
        self.model = model

    def is_healthy(self) -> bool:
        return True

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        # Check if the query is a rewrite request or QA request
        content = messages[-1]["content"] if messages else ""
        if "Rewrite the following" in content:
            return "Section 43A IT Act"
        return "Based on the provided context, Section 43A [Information Technology Act, 2000 - Section 43A, Page 12] applies."

    def chat_stream(self, messages: list[dict[str, str]], temperature: float = 0.1, max_tokens: int = 1024):
        tokens = ["Based", " on", " the", " provided", " context,", " Section", " 43A", " [Information Technology Act, 2000 - Section 43A, Page 12]", " applies."]
        for token in tokens:
            yield token

    def close(self) -> None:
        pass


class MockBM25Retriever:
    def rebuild_from_vector_store(self, vector_store: Any) -> None:
        pass

    def retrieve(self, query: str, top_k: int = 10, *args: Any, **kwargs: Any) -> list[SearchResult]:
        return [
            SearchResult(
                chunk_id="test-1",
                content="Mocked similarity search content",
                score=0.95,
                metadata=ChunkMetadata(
                    act_name="Information Technology Act, 2000",
                    section_number="Section 43A",
                    article_number="",
                    chapter="",
                    page_number=12,
                    source_file="it_act.pdf"
                ),
                rank=1,
                retrieval_method="bm25"
            )
        ]


# ── Monkeypatch Backend Dependency Singletons ────────────────────

import backend.dependencies as deps

# We override the singleton getters to return our mock services
deps.get_embedding_service_dependency = lambda: MockEmbeddingService()
deps.get_vector_store_dependency = lambda: MockVectorStore()
deps.get_bm25_retriever_dependency = lambda: MockBM25Retriever()
deps.get_reranker_dependency = lambda: MockReranker()
deps.get_ollama_client_dependency = lambda: MockOllamaClient()



@pytest.fixture(scope="session")
def client():
    """Session-scoped test client with mocked dependencies."""
    # Ensure api key checks are bypassed or match the test configurations
    # Set target environment variables
    os.environ["API_KEY"] = "test-secret-key"
    
    from fastapi.testclient import TestClient
    from backend.main import app
    
    with TestClient(app) as test_client:
        yield test_client
