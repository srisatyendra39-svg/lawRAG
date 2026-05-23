from __future__ import annotations

import math
import warnings
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import batch_to_device
from tqdm import tqdm

from configs.settings import get_settings, Settings
from utils.logger import get_logger


logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using sentence-transformers."""

    def __init__(self, model_name: str, device: str = "cpu", batch_size: int = 32) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.model = self._load_model(model_name, device)

    def _load_model(self, model_name: str, device: str) -> SentenceTransformer:
        try:
            model = SentenceTransformer(model_name, device=device)
        except Exception as exc:
            if device != "cpu":
                warnings.warn("Falling back to cpu because the model could not load on the requested device.")
                model = SentenceTransformer(model_name, device="cpu")
            else:
                raise RuntimeError(f"Failed to load embedding model: {model_name}") from exc
        logger.info("Loaded embedding model", model_name=model_name, device=device)
        return model

    def warmup(self) -> None:
        """Warm up the embedding model with a dummy string."""
        self.embed_texts(["Warm up the sentence transformer model."])

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of texts and return normalized vectors."""
        if not texts:
            raise ValueError("No texts provided for embedding")
        embeddings = []
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Embedding batches", unit="batch"):
            batch = texts[i : i + self.batch_size]
            vectors = self.model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
            normalized = self._normalize(vectors)
            embeddings.extend(normalized.tolist())
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Encode a single query and return a normalized vector."""
        if not query.strip():
            raise ValueError("Query text must not be empty")
        vector = self.model.encode(query, convert_to_numpy=True, show_progress_bar=False)
        normalized = self._normalize(vector)
        if normalized.ndim == 2 and normalized.shape[0] == 1:
            normalized = normalized[0]
        return normalized.tolist()

    def get_embedding_dimension(self) -> int:
        """Return the embedding vector dimensionality."""
        return self.model.get_sentence_embedding_dimension()

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """Apply L2 normalization to the embedding vectors."""
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


class LangChainEmbeddingAdapter(Embeddings):
    """Adapter so the embedding service can be used by LangChain."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return self.embedding_service.embed_texts(documents)

    def embed_query(self, query: str) -> List[float]:
        return self.embedding_service.embed_query(query)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return a singleton embedding service instance."""
    settings = get_settings()
    model_name = settings.embedding_model
    device = settings.embedding_device
    batch_size = settings.embedding_batch_size
    service = EmbeddingService(model_name=model_name, device=device, batch_size=batch_size)
    service.warmup()
    return service


@lru_cache(maxsize=1)
def get_langchain_embedding_adapter() -> LangChainEmbeddingAdapter:
    """Return a singleton LangChain adapter for embeddings."""
    service = get_embedding_service()
    return LangChainEmbeddingAdapter(embedding_service=service)
