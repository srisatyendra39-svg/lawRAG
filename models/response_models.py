from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChunkMetadata(BaseModel):
    """Metadata describing a legal document chunk."""

    act_name: str = Field(..., description="Name of the legal act")
    section_number: str = Field(..., description="Section number associated with the chunk")
    article_number: str = Field(..., description="Article number associated with the chunk")
    chapter: str = Field(..., description="Chapter associated with the chunk")
    page_number: int = Field(..., ge=0, description="Page number in the source document (0 = unknown)")
    source_file: str = Field(..., description="Source PDF filename")
    kb_id: str = Field(default="global", description="Knowledge base ID")
    doc_category: str = Field(default="global", description="Category of document (global/custom)")

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "example": {
            "act_name": "Information Technology Act, 2000",
            "section_number": "Section 43A",
            "article_number": "",
            "chapter": "Chapter XI",
            "page_number": 12,
            "source_file": "IT_Act_2000.pdf",
            "kb_id": "global",
            "doc_category": "global",
        }
    })

    @field_validator("section_number", "article_number", "chapter", "source_file")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        return value.strip()


class SearchResult(BaseModel):
    """A single result returned by a search operation."""

    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    content: str = Field(..., description="Text content of the chunk")
    score: float = Field(..., description="Relevance score for the chunk")
    metadata: ChunkMetadata = Field(..., description="Structured metadata for the chunk")
    rank: int = Field(..., ge=1, description="Rank of the chunk in the result set")
    retrieval_method: Optional[str] = Field(None, description="Retrieval method used for this result")

    model_config = ConfigDict(extra="forbid")


class SearchResponse(BaseModel):
    """Response payload for retrieval-only searches."""

    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Ordered list of search results")
    retrieval_method: str = Field(..., description="Primary retrieval method used")
    total_results: int = Field(..., ge=0, description="Total number of matches")
    latency_ms: float = Field(..., ge=0.0, description="Elapsed time in milliseconds")

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "example": {
            "query": "What is Section 43A?",
            "results": [],
            "retrieval_method": "hybrid",
            "total_results": 5,
            "latency_ms": 200.0,
        }
    })


class Citation(BaseModel):
    """Citation details for a legal answer."""

    act_name: str = Field(..., description="Name of the act cited")
    section: str = Field(..., description="Section referenced in the citation")
    article: str = Field(..., description="Article referenced in the citation")
    chapter: str = Field(..., description="Chapter referenced in the citation")
    page: int = Field(..., ge=0, description="Page number cited (0 = not specified)")
    quote: str = Field(..., description="Quoted text used in the answer")
    relevance_score: Optional[float] = Field(None, description="Relevance score of the cited passage")

    model_config = ConfigDict(extra="forbid")


class RAGResponse(BaseModel):
    """Response payload for the RAG question answering endpoint."""

    question: str = Field(..., description="Original user question")
    answer: str = Field(..., description="Generated answer from the RAG pipeline")
    citations: List[Citation] = Field(..., description="Citations referenced in the answer")
    rewritten_query: Optional[str] = Field(None, description="Rewritten query used for retrieval")
    latency_ms: float = Field(..., ge=0.0, description="Total latency for the RAG request")
    model_used: str = Field(..., description="LLM model used to generate the answer")

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class IngestResponse(BaseModel):
    """Response payload for ingestion operations."""

    status: str = Field(..., description="Ingestion status")
    chunks_created: int = Field(..., ge=0, description="Number of chunks created")
    act_name: str = Field(..., description="Act name ingested")
    processing_time_ms: float = Field(..., ge=0.0, description="Time taken in milliseconds")
    message: str = Field(..., description="Human-readable status message")

    model_config = ConfigDict(extra="forbid")


class EvaluationResult(BaseModel):
    """Evaluation metrics produced by the RAGAS pipeline."""

    faithfulness: float = Field(..., ge=0.0, le=1.0, description="Faithfulness score")
    answer_relevancy: float = Field(..., ge=0.0, le=1.0, description="Answer relevancy score")
    context_precision: float = Field(..., ge=0.0, le=1.0, description="Context precision score")
    context_recall: float = Field(..., ge=0.0, le=1.0, description="Context recall score")

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "example": {
            "faithfulness": 0.85,
            "answer_relevancy": 0.9,
            "context_precision": 0.8,
            "context_recall": 0.75,
        }
    })
