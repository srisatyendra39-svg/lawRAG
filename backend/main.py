from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, FastAPI, Depends, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from backend.dependencies import (
    get_answer_generator_dependency,
    get_bm25_retriever_dependency,
    get_embedding_service_dependency,
    get_hybrid_retriever_dependency,
    get_ingestion_pipeline_dependency,
    get_query_rewriter_dependency,
    get_reranker_dependency,
    get_semantic_retriever_dependency,
    get_settings_dependency,
    get_vector_store_dependency,
    get_ollama_client_dependency,
    verify_api_key,
)
from backend.routers.evaluate import router as evaluate_router
from backend.routers.ingest import router as ingest_router
from backend.routers.search import router as search_router
from backend.routers.kb import router as kb_router
from configs.settings import get_settings
from utils.logger import get_logger, correlation_id_var

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup Logic ───────────────────────────────────────────
    embedding_service = get_embedding_service_dependency()
    embedding_service.warmup()
    
    reranker = get_reranker_dependency()
    reranker.warmup()
    
    vector_store = get_vector_store_dependency()
    chroma_status = "connected" if vector_store.collection_exists() else "empty"
    
    ollama_client = get_ollama_client_dependency()
    llm_status = "connected" if ollama_client.is_healthy() else "unreachable"
    
    bm25_retriever = get_bm25_retriever_dependency()
    bm25_retriever.rebuild_from_vector_store(vector_store)
    
    logger.info(
        "Legal RAG System Ready [SUCCESS]",
        chroma_status=chroma_status,
        ollama_status=llm_status,
        total_chunks=vector_store.get_collection_stats().get("total_chunks", 0),
    )
    
    yield
    
    # ── Shutdown Logic ──────────────────────────────────────────
    logger.info("Shutting down Legal RAG Assistant API")
    ollama_client.close()


app = FastAPI(
    title="Legal RAG Assistant API",
    version=settings.app_version,
    lifespan=lifespan,
)


# Correlation ID and latency tracking middleware
@app.middleware("http")
async def add_correlation_id_and_latency(request: Request, call_next):
    # Extract correlation ID from incoming header or generate a new one
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    # Set context-local correlation ID for logging
    token = correlation_id_var.set(correlation_id)
    
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        # Re-raise to allow custom exception handler to format it
        raise exc
    finally:
        process_time_ms = (time.perf_counter() - start_time) * 1000
        # Reset context variable
        correlation_id_var.reset(token)
        
    # Attach correlation ID and response time headers to outgoing response
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time-Ms"] = f"{process_time_ms:.2f}"
    return response


app.add_middleware(
    CORSMiddleware,
    # NOTE: For production, replace "*" with explicit frontend origins
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Custom exception handlers for structured responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "success": False,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR",
            "success": False,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Global unhandled exception caught")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "success": False,
        },
    )


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    return {
        "message": "Legal RAG Assistant API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
def health() -> dict[str, object]:
    vector_store = get_vector_store_dependency()
    ollama_client = get_ollama_client_dependency()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "chroma_status": "connected" if vector_store.collection_exists() else "empty",
        "ollama_status": "connected" if ollama_client.is_healthy() else "unreachable",
        "total_chunks": vector_store.get_collection_stats().get("total_chunks", 0),
        "models": {
            "embedding": settings.embedding_model,
            "reranker": settings.reranker_model,
        },
    }


app.include_router(
    ingest_router,
    prefix="/api/v1",
    tags=["Ingestion"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    search_router,
    prefix="/api/v1",
    tags=["Search"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    evaluate_router,
    prefix="/api/v1",
    tags=["Evaluation"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    kb_router,
    prefix="/api/v1",
    tags=["Knowledge Base"],
    dependencies=[Depends(verify_api_key)],
)

# Serve modern premium frontend portal
from fastapi.responses import RedirectResponse

@app.get("/portal", include_in_schema=False)
def redirect_to_portal():
    return RedirectResponse(url="/portal/")

app.mount("/portal", StaticFiles(directory="frontend_modern", html=True), name="portal")

