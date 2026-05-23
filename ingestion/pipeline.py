from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

from embeddings.embedder import get_embedding_service
from ingestion.metadata_extractor import LegalMetadataExtractor
from ingestion.document_parser import DocumentParser, DocumentParserError
from ingestion.pdf_loader import PDFLoader
from models.request_models import IngestRequest
from models.response_models import ChunkMetadata, IngestResponse
from vectorstore.chroma_store import LegalVectorStore
from chunking.legal_chunker import LegalChunker
from utils.logger import get_logger


logger = get_logger(__name__)


class IngestionPipeline:
    """Orchestrator for document ingestion and vector indexing."""

    def __init__(
        self,
        document_parser: DocumentParser,
        metadata_extractor: LegalMetadataExtractor,
        chunker: LegalChunker,
        vector_store: LegalVectorStore,
        act_mappings: dict[str, str] | None = None,
    ) -> None:
        self.document_parser = document_parser
        self.metadata_extractor = metadata_extractor
        self.chunker = chunker
        self.vector_store = vector_store
        if act_mappings is None:
            try:
                from configs.settings import get_settings
                self.act_mappings = get_settings().act_mappings
            except Exception:
                self.act_mappings = {
                    "it_act": "Information Technology Act, 2000",
                    "information_technology": "Information Technology Act, 2000",
                    "constitution": "Constitution of India",
                    "dpdp": "Digital Personal Data Protection Act, 2023",
                    "data_protection": "Digital Personal Data Protection Act, 2023",
                    "rti": "Right to Information Act, 2005",
                }
        else:
            self.act_mappings = act_mappings

    def ingest_document(
        self,
        file_path: Path,
        act_name: str,
        overwrite: bool = False,
        kb_id: str = "global",
        doc_category: str = "global",
    ) -> IngestResponse:
        """Ingest a single PDF, DOCX, or TXT document end to end."""
        start = time.perf_counter()
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        try:
            pages = self.document_parser.parse(file_path)
        except Exception as exc:
            logger.error("Document parsing failed", error=str(exc), file_path=str(file_path))
            raise

        if overwrite:
            if kb_id == "global":
                deleted = self.vector_store.delete_by_act(act_name)
            else:
                # Delete by source file within the specific KB to allow partial updates
                deleted = self.vector_store.collection.delete(
                    where={"$and": [{"kb_id": kb_id}, {"source_file": file_path.name}]}
                )
                deleted = len(deleted.get("ids", [])) if isinstance(deleted, dict) else 0
            logger.info("Existing document data removed before ingestion", file_path=file_path.name, deleted=deleted)

        raw_chunks = self.chunker.chunk_document(pages, source_file=file_path.name)
        completed_chunks = []
        for chunk in raw_chunks:
            metadata = self.metadata_extractor.extract(chunk.raw_content, chunk.metadata.page_number, file_path.name)
            metadata.kb_id = kb_id
            metadata.doc_category = doc_category
            if doc_category == "custom" and not metadata.act_name:
                metadata.act_name = act_name or file_path.stem

            updated_chunk = type(chunk)(
                chunk_id=chunk.chunk_id,
                content=self.chunker.add_context_prefix(chunk.raw_content, metadata),
                raw_content=chunk.raw_content,
                metadata=metadata,
                char_count=chunk.char_count,
                word_count=chunk.word_count,
            )
            completed_chunks.append(updated_chunk)

        added = self.vector_store.add_chunks(completed_chunks)
        elapsed = (time.perf_counter() - start) * 1000
        response = IngestResponse(
            status="success",
            chunks_created=added,
            act_name=act_name or file_path.stem,
            processing_time_ms=elapsed,
            message=f"Ingested {added} chunks for {act_name or file_path.name} in KB '{kb_id}'",
        )
        logger.info("Document ingested", file_path=str(file_path), act_name=act_name, chunks_created=added, kb_id=kb_id)
        return response

    def ingest_all_documents(self, data_dir: Path, overwrite: bool = True) -> List[IngestResponse]:
        """Ingest all PDF documents found in the raw data directory."""
        responses: List[IngestResponse] = []
        for pdf_path in sorted(data_dir.glob("*.pdf")):
            act_name = self._infer_act_name(pdf_path.name)
            try:
                response = self.ingest_document(pdf_path, act_name, overwrite=overwrite)
            except Exception as exc:
                logger.error("Failed to ingest document", file_path=str(pdf_path), error=str(exc))
                response = IngestResponse(
                    status="failed",
                    chunks_created=0,
                    act_name=act_name,
                    processing_time_ms=0.0,
                    message=str(exc),
                )
            responses.append(response)
        return responses

    def _infer_act_name(self, filename: str) -> str:
        name = filename.lower()
        for substring, act in self.act_mappings.items():
            if substring in name:
                return act
        return "Unknown Act"

    def get_ingestion_stats(self) -> Dict[str, int]:
        """Return summary statistics from the vector store."""
        stats = self.vector_store.get_collection_stats()
        return {
            "total_chunks": stats.get("total_chunks", 0),
            "acts_indexed": len(stats.get("chunks_per_act", {})),
        }


def build_ingestion_pipeline() -> IngestionPipeline:
    """Create a fully wired ingestion pipeline."""
    from configs.settings import get_settings
    from embeddings.embedder import get_langchain_embedding_adapter

    settings = get_settings()
    pdf_loader = PDFLoader()
    document_parser = DocumentParser(pdf_loader=pdf_loader)
    return IngestionPipeline(
        document_parser=document_parser,
        metadata_extractor=LegalMetadataExtractor(act_mappings=settings.act_mappings),
        chunker=LegalChunker(),
        vector_store=LegalVectorStore(
            persist_dir=str(settings.chroma_persist_dir),
            collection_name=settings.chroma_collection_name,
            embedding_service=get_langchain_embedding_adapter(),
        ),
        act_mappings=settings.act_mappings,
    )

