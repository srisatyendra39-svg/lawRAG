from __future__ import annotations

import os
from pathlib import Path
import pytest
import fitz

from chunking.legal_chunker import LegalChunker
from ingestion.metadata_extractor import LegalMetadataExtractor
from ingestion.pdf_loader import PDFLoader
from ingestion.document_parser import DocumentParser
from ingestion.pipeline import IngestionPipeline
from vectorstore.chroma_store import LegalVectorStore
from retrievers.semantic_retriever import SemanticRetriever
from retrievers.bm25_retriever import BM25Retriever
from retrievers.hybrid_retriever import HybridRetriever
from generators.ollama_client import OllamaClient
from generators.answer_generator import LegalAnswerGenerator
from tests.conftest import MockEmbeddingService, MockOllamaClient


def create_sample_pdf(path: Path, texts: list[str]) -> None:
    doc = fitz.open()
    for text in texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_full_pipeline_integration(tmp_path: Path) -> None:
    # 1. Setup temporary files
    pdf_path = tmp_path / "it_act.pdf"
    create_sample_pdf(
        pdf_path,
        [
            "Section 43A: Compensation for failure to protect data. If a body corporate fails to protect sensitive personal data, it shall be liable to pay damages.",
            "Section 66A: Punishment for sending offensive messages through communication service."
        ]
    )

    # 2. Setup mock components and real orchestration classes
    embedding_service = MockEmbeddingService()
    vector_store = LegalVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_integration_collection",
        embedding_service=embedding_service,
    )
    
    act_mappings = {
        "it_act": "Information Technology Act, 2000"
    }

    pipeline = IngestionPipeline(
        document_parser=DocumentParser(pdf_loader=PDFLoader()),
        metadata_extractor=LegalMetadataExtractor(act_mappings=act_mappings),
        chunker=LegalChunker(chunk_size=100, chunk_overlap=10),
        vector_store=vector_store,
        act_mappings=act_mappings,
    )

    bm25_retriever = BM25Retriever()
    semantic_retriever = SemanticRetriever(vector_store=vector_store)
    hybrid_retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        bm25_retriever=bm25_retriever,
        alpha=0.5
    )

    # 3. Execute Ingestion
    ingest_resp = pipeline.ingest_document(pdf_path, act_name="Information Technology Act, 2000", overwrite=True)
    assert ingest_resp.status == "success"
    assert ingest_resp.chunks_created > 0

    # 4. Rebuild sparse index
    bm25_retriever.rebuild_from_vector_store(vector_store)

    # 5. Execute retrieval
    results = hybrid_retriever.retrieve(query="Compensation for failure to protect data", top_k=2)
    assert len(results) > 0
    first_result = results[0]
    assert first_result.metadata.act_name == "Information Technology Act, 2000"
    assert "Section 43A" in first_result.content or "Section 66A" in first_result.content

    # 6. Execute answer generation
    ollama_client = MockOllamaClient()
    answer_generator = LegalAnswerGenerator(ollama_client=ollama_client)
    
    context = "\n\n".join(item.content for item in results)
    rag_response = answer_generator.generate(
        question="What is the compensation for failure to protect data?",
        context=context,
    )
    
    assert rag_response.question == "What is the compensation for failure to protect data?"
    assert len(rag_response.answer) > 0
    assert len(rag_response.citations) > 0
    assert rag_response.citations[0].act_name == "Information Technology Act, 2000"
