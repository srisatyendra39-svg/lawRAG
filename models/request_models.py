from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    """Request body for ingesting a PDF document."""

    file_path: str = Field(..., description="Local file path to the PDF document")
    act_name: str = Field(..., description="Name of the act to associate with this ingestion")
    overwrite: bool = Field(False, description="Whether to overwrite existing indexed chunks")

    model_config = {"extra": "forbid"}

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("file_path must not be empty")
        return value


class SearchRequest(BaseModel):
    """Request body for retrieval-only search operations."""

    query: str = Field(..., description="Search query string")
    top_k: int = Field(5, ge=1, description="Number of results to return")
    act_filter: Optional[str] = Field(None, description="Optional act name filter")
    chapter_filter: Optional[str] = Field(None, description="Optional chapter filter")
    use_reranker: bool = Field(True, description="Whether to apply reranking")
    hybrid: bool = Field(True, description="Whether to use hybrid retrieval")
    kb_id: Optional[str] = Field("global", description="Optional target knowledge base ID")
    search_scope: str = Field("global", description="Search scope: global, custom, or combined")
    hybrid_alpha: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional hybrid alpha weight override")

    model_config = {"extra": "forbid"}


class QueryRequest(BaseModel):
    """Request body for RAG question answering."""

    question: str = Field(..., description="User question to answer")
    top_k: int = Field(5, ge=1, description="Number of top chunks to retrieve")
    act_filter: Optional[str] = Field(None, description="Optional act name filter")
    rewrite_query: bool = Field(True, description="Whether to rewrite the user query")
    stream: bool = Field(False, description="Whether to stream the answer token-by-token")
    kb_id: Optional[str] = Field("global", description="Optional target knowledge base ID")
    search_scope: str = Field("global", description="Search scope: global, custom, or combined")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Optional LLM temperature override")
    hybrid_alpha: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional hybrid alpha weight override")

    model_config = {"extra": "forbid"}


class KBCreateRequest(BaseModel):
    """Request body for creating a knowledge base."""
    kb_id: str = Field(..., description="Unique ID for the knowledge base")
    kb_name: str = Field(..., description="Friendly name for the knowledge base")

    model_config = {"extra": "forbid"}


class EvaluationRequest(BaseModel):
    """Request body for evaluation runs."""

    questions: List[str] = Field(..., description="List of evaluation questions")
    ground_truths: Optional[List[str]] = Field(None, description="Optional list of ground truth answers")

    model_config = {"extra": "forbid"}

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("questions must contain at least one item")
        return [question.strip() for question in value if question.strip()]

