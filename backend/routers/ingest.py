from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, File, Form, UploadFile

from backend.dependencies import (
    get_bm25_retriever_dependency,
    get_ingestion_pipeline_dependency,
    get_settings_dependency,
    get_vector_store_dependency,
)
from configs.settings import Settings
from models.request_models import IngestRequest
from models.response_models import IngestResponse
from retrievers.bm25_retriever import BM25Retriever
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/document", response_model=IngestResponse)
def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    pipeline=Depends(get_ingestion_pipeline_dependency),
    bm25_retriever: BM25Retriever = Depends(get_bm25_retriever_dependency),
    settings: Settings = Depends(get_settings_dependency),
) -> IngestResponse:
    try:
        file_path = Path(request.file_path).resolve()
        # Security: prevent path traversal — file must be within raw_data_dir
        allowed_dir = settings.raw_data_dir.resolve()
        if not str(file_path).startswith(str(allowed_dir)):
            raise HTTPException(
                status_code=403,
                detail=f"File path must be within the configured data directory: {allowed_dir}",
            )
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        if not file_path.suffix.lower() == ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")
        response = pipeline.ingest_document(file_path=file_path, act_name=request.act_name, overwrite=request.overwrite)
        background_tasks.add_task(_rebuild_bm25_index, bm25_retriever, settings)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ingest document failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


def _rebuild_bm25_index(bm25_retriever: BM25Retriever, settings: Settings) -> None:
    from backend.dependencies import get_vector_store_dependency

    vector_store = get_vector_store_dependency()
    bm25_retriever.rebuild_from_vector_store(vector_store)


@router.post("/all", response_model=List[IngestResponse])
def ingest_all_documents(
    background_tasks: BackgroundTasks,
    pipeline=Depends(get_ingestion_pipeline_dependency),
) -> List[IngestResponse]:
    try:
        raw_dir = Path("data/raw")
        if not raw_dir.exists():
            raise HTTPException(status_code=404, detail="Raw data directory missing")
        responses = pipeline.ingest_all_documents(raw_dir)
        return responses
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ingest all documents failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
def ingest_status(
    vector_store=Depends(get_vector_store_dependency),
) -> dict[str, object]:
    try:
        stats = vector_store.get_collection_stats()
        return {
            "acts_ingested": stats.get("chunks_per_act", {}),
            "total_chunks": stats.get("total_chunks", 0),
            "status": "ready",
        }
    except Exception as exc:
        logger.error("Ingest status failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upload", response_model=IngestResponse)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    act_name: str = Form(""),
    kb_id: str = Form("global"),
    overwrite: bool = Form(False),
    pipeline=Depends(get_ingestion_pipeline_dependency),
    bm25_retriever: BM25Retriever = Depends(get_bm25_retriever_dependency),
    settings: Settings = Depends(get_settings_dependency),
) -> IngestResponse:
    try:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in [".pdf", ".docx", ".txt"]:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Only PDF, DOCX, and TXT are supported."
            )
        
        # Save file to a temporary location in data/tmp
        tmp_dir = Path("data/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        file_path = tmp_dir / file.filename
        
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(file.file.read())
            
            doc_category = "global" if kb_id == "global" else "custom"
            
            # If overwrite is true and it's a custom KB, clean up chunks from the same source file name first
            # pipeline.ingest_document handles overwrite internally, but let's pass parameters correctly
            response = pipeline.ingest_document(
                file_path=file_path,
                act_name=act_name or Path(file.filename).stem,
                overwrite=overwrite,
                kb_id=kb_id,
                doc_category=doc_category
            )
            
            # If successful, register file in KB registry
            if kb_id != "global" and response.status == "success":
                from backend.routers.kb import _load_registry, _save_registry
                registry = _load_registry()
                if kb_id in registry:
                    if file.filename not in registry[kb_id]["files"]:
                        registry[kb_id]["files"].append(file.filename)
                        _save_registry(registry)
            
            background_tasks.add_task(_rebuild_bm25_index, bm25_retriever, settings)
            return response
        finally:
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {file_path}: {e}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upload document failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")

