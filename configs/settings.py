from __future__ import annotations

import warnings
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Flat application settings loaded directly from environment variables.

    Every field uses an explicit ``env=`` alias that matches the .env file keys,
    so there is no need for nested models or ``env_nested_delimiter``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        arbitrary_types_allowed=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = Field("Legal RAG Assistant", alias="APP_NAME", description="Human-readable application name")
    app_version: str = Field("0.0.1", alias="APP_VERSION", description="Application version")
    debug: bool = Field(False, alias="DEBUG", description="Enable debug mode")
    log_level: str = Field("INFO", alias="LOG_LEVEL", description="Default log level")

    # ── API Server ───────────────────────────────────────────────
    api_host: str = Field("0.0.0.0", alias="API_HOST", description="Host for FastAPI server")
    api_port: int = Field(8000, alias="API_PORT", description="Port for FastAPI server")
    api_reload: bool = Field(False, alias="API_RELOAD", description="Enable auto reload during development")
    api_key: Optional[str] = Field(None, alias="API_KEY", description="Optional API key for securing backend endpoints")
    # ── Embeddings ───────────────────────────────────────────────
    embedding_model: str = Field(
        "sentence-transformers/all-mpnet-base-v2",
        alias="EMBEDDING_MODEL",
        description="Sentence Transformers embedding model",
    )
    embedding_device: str = Field("cpu", alias="EMBEDDING_DEVICE", description="Device for embedding inference")
    embedding_batch_size: int = Field(32, alias="EMBEDDING_BATCH_SIZE", description="Batch size for embedding requests")

    # ── LLM ──────────────────────────────────────────────────────
    llm_provider: str = Field("ollama", alias="LLM_PROVIDER", description="Local LLM provider")
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL", description="Base URL for Ollama API")
    ollama_model: str = Field("llama3", alias="OLLAMA_MODEL", description="Ollama model name")
    llm_temperature: float = Field(0.1, alias="LLM_TEMPERATURE", description="LLM temperature")
    llm_max_tokens: int = Field(1024, alias="LLM_MAX_TOKENS", description="Maximum number of LLM tokens")

    @field_validator("llm_temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        if not 0.0 <= value <= 2.0:
            raise ValueError("LLM_TEMPERATURE must be between 0.0 and 2.0")
        return value

    # ── Vector DB ────────────────────────────────────────────────
    chroma_persist_dir: Path = Field(Path("data/chroma"), alias="CHROMA_PERSIST_DIR", description="Directory for ChromaDB persistence")
    chroma_collection_name: str = Field("legal_docs", alias="CHROMA_COLLECTION_NAME", description="ChromaDB collection name")

    # ── Retrieval ────────────────────────────────────────────────
    retriever_top_k: int = Field(10, alias="RETRIEVER_TOP_K", description="Default top K for retrieval")
    reranker_top_k: int = Field(5, alias="RERANKER_TOP_K", description="Top K candidates for reranking")
    hybrid_alpha: float = Field(0.5, alias="HYBRID_ALPHA", description="Hybrid retrieval weighting between semantic and BM25")
    bm25_k1: float = Field(1.5, alias="BM25_K1", description="BM25 k1 parameter")
    bm25_b: float = Field(0.75, alias="BM25_B", description="BM25 b parameter")

    @field_validator("hybrid_alpha")
    @classmethod
    def validate_alpha(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("HYBRID_ALPHA must be between 0.0 and 1.0")
        return value

    # ── Reranker ─────────────────────────────────────────────────
    reranker_model: str = Field(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        alias="RERANKER_MODEL",
        description="Cross-encoder model for reranking",
    )

    # ── Chunking ─────────────────────────────────────────────────
    chunk_size: int = Field(1000, alias="CHUNK_SIZE", description="Preferred character length for chunks")
    chunk_overlap: int = Field(200, alias="CHUNK_OVERLAP", description="Overlap size between adjacent chunks")

    # ── Data Paths ───────────────────────────────────────────────
    raw_data_dir: Path = Field(Path("data/raw"), alias="RAW_DATA_DIR", description="Directory containing raw PDF documents")
    processed_data_dir: Path = Field(Path("data/processed"), alias="PROCESSED_DATA_DIR", description="Directory for processed outputs")

    # ── Act Detection ────────────────────────────────────────────
    act_mappings: dict[str, str] = Field(
        default={
            "it_act": "Information Technology Act, 2000",
            "information_technology": "Information Technology Act, 2000",
            "constitution": "Constitution of India",
            "dpdp": "Digital Personal Data Protection Act, 2023",
            "data_protection": "Digital Personal Data Protection Act, 2023",
            "rti": "Right to Information Act, 2005",
        },
        alias="ACT_MAPPINGS",
        description="Mapping of filename substrings to formal Act names",
    )

    # ── Evaluation ───────────────────────────────────────────────
    eval_sample_size: int = Field(20, alias="EVAL_SAMPLE_SIZE", description="Number of queries used during evaluation")

    @field_validator("eval_sample_size")
    @classmethod
    def validate_sample_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("EVAL_SAMPLE_SIZE must be positive")
        return value

    def __repr__(self) -> str:
        return f"Settings(app_name={self.app_name!r}, version={self.app_version!r}, debug={self.debug})"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a singleton Settings instance.

    Attempt to load from environment/.env; if validation fails, create
    minimal default settings so the app can import without an environment
    file (useful for tests).
    """
    try:
        settings = Settings()  # type: ignore[call-arg]
    except Exception as exc:
        warnings.warn(
            f"Failed to load settings from .env, using defaults: {exc}",
            stacklevel=2,
        )
        # Ensure data directories exist
        for dir_path in ("data/raw", "data/processed", "data/chroma", "data/evaluation", "data/logs"):
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]

    # Ensure critical directories exist
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
    return settings
