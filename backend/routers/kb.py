import json
import re
import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from backend.dependencies import (
    get_bm25_retriever_dependency,
    get_vector_store_dependency,
    get_settings_dependency,
)
from models.request_models import KBCreateRequest
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

REGISTRY_PATH = Path("data/knowledge_bases.json")


def _load_registry() -> Dict[str, Dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load KB registry", error=str(e))
        return {}


def _save_registry(registry: Dict[str, Dict[str, Any]]) -> None:
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4)
    except Exception as e:
        logger.error("Failed to save KB registry", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save KB registry")


@router.post("/create", response_model=dict)
def create_kb(request: KBCreateRequest) -> dict:
    kb_id = request.kb_id.strip().lower()
    kb_name = request.kb_name.strip()

    if not kb_id:
        raise HTTPException(status_code=400, detail="kb_id cannot be empty")
    if not kb_name:
        raise HTTPException(status_code=400, detail="kb_name cannot be empty")
    if kb_id == "global":
        raise HTTPException(status_code=400, detail="'global' is a reserved knowledge base ID")

    if not re.match(r"^[a-z0-9_-]+$", kb_id):
        raise HTTPException(
            status_code=400,
            detail="kb_id can only contain lowercase alphanumeric characters, underscores, and hyphens",
        )

    registry = _load_registry()
    if kb_id in registry:
        raise HTTPException(status_code=400, detail=f"Knowledge base with ID '{kb_id}' already exists")

    registry[kb_id] = {
        "kb_id": kb_id,
        "kb_name": kb_name,
        "files": [],
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    _save_registry(registry)
    logger.info("Knowledge base created", kb_id=kb_id, kb_name=kb_name)
    return {
        "status": "success",
        "message": f"Knowledge base '{kb_name}' created successfully",
        "kb_id": kb_id,
    }


@router.get("/list", response_model=List[dict])
def list_kbs() -> List[dict]:
    registry = _load_registry()
    # Always include global
    kbs = [
        {
            "kb_id": "global",
            "kb_name": "Global Database (Default)",
            "files": [],
            "created_at": "",
        }
    ]
    kbs.extend(registry.values())
    return kbs


@router.post("/delete", response_model=dict)
def delete_kb(
    kb_id: str,
    background_tasks: BackgroundTasks,
    vector_store=Depends(get_vector_store_dependency),
    bm25_retriever=Depends(get_bm25_retriever_dependency),
) -> dict:
    kb_id = kb_id.strip().lower()
    if kb_id == "global":
        raise HTTPException(status_code=400, detail="Cannot delete default 'global' knowledge base")

    registry = _load_registry()
    if kb_id not in registry:
        raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")

    deleted_chunks = vector_store.delete_by_kb(kb_id)
    background_tasks.add_task(_rebuild_bm25, bm25_retriever, vector_store)

    kb_name = registry[kb_id]["kb_name"]
    del registry[kb_id]
    _save_registry(registry)

    logger.info("Knowledge base deleted", kb_id=kb_id, deleted_chunks=deleted_chunks)
    return {
        "status": "success",
        "message": f"Knowledge base '{kb_name}' and its {deleted_chunks} chunks deleted successfully",
    }


def _rebuild_bm25(bm25_retriever, vector_store):
    bm25_retriever.rebuild_from_vector_store(vector_store)
