import json
import time
from collections.abc import Generator
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.dependencies import (
    get_answer_generator_dependency,
    get_bm25_retriever_dependency,
    get_hybrid_retriever_dependency,
    get_query_rewriter_dependency,
    get_reranker_dependency,
    get_semantic_retriever_dependency,
    get_settings_dependency,
)
from models.request_models import QueryRequest, SearchRequest
from models.response_models import Citation, RAGResponse, SearchResponse, SearchResult
from prompts.query_prompts import format_context
from retrievers.bm25_retriever import BM25Retriever
from retrievers.hybrid_retriever import HybridRetriever
from retrievers.semantic_retriever import SemanticRetriever
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/search", tags=["Search"])


def map_citations_to_results(
    citations: list[Citation],
    results: list[SearchResult],
    answer_text: str
) -> list[Citation]:
    """
    Map citations to retrieved results to populate their quote, chapter,
    page and relevance_score. If citations list is empty, generate citations
    directly from top retrieved results.
    """
    mapped_citations: list[Citation] = []
    matched_ids = set()

    # Phase 1: Try to match LLM-provided citations to retrieved results
    for cite in citations:
        best_match = None
        cite_act = cite.act_name.lower().strip()
        cite_sec = cite.section.lower().strip()
        cite_art = cite.article.lower().strip()

        for res in results:
            res_act = res.metadata.act_name.lower().strip()
            res_sec = res.metadata.section_number.lower().strip()
            res_art = res.metadata.article_number.lower().strip()

            # Act name check (supporting partial matches like IT Act vs Information Technology Act)
            act_matches = cite_act in res_act or res_act in cite_act
            
            # Section/Article check
            sec_matches = False
            if cite_sec and res_sec:
                sec_matches = cite_sec in res_sec or res_sec in cite_sec
            elif cite_art and res_art:
                sec_matches = cite_art in res_art or res_art in cite_art

            if act_matches and sec_matches:
                best_match = res
                break

        if best_match:
            matched_ids.add(best_match.chunk_id)
            mapped_citations.append(Citation(
                act_name=best_match.metadata.act_name,
                section=best_match.metadata.section_number,
                article=best_match.metadata.article_number,
                chapter=best_match.metadata.chapter,
                page=best_match.metadata.page_number if cite.page == 0 else cite.page,
                quote=best_match.content,
                relevance_score=best_match.score
            ))
        else:
            # Fallback matching by content search
            fallback_match = None
            if cite_sec:
                for res in results:
                    if cite_sec in res.content.lower():
                        fallback_match = res
                        break
            if fallback_match:
                matched_ids.add(fallback_match.chunk_id)
                mapped_citations.append(Citation(
                    act_name=fallback_match.metadata.act_name,
                    section=fallback_match.metadata.section_number,
                    article=fallback_match.metadata.article_number,
                    chapter=fallback_match.metadata.chapter,
                    page=fallback_match.metadata.page_number if cite.page == 0 else cite.page,
                    quote=fallback_match.content,
                    relevance_score=fallback_match.score
                ))
            else:
                # If no retrieved match, keep it as is (quote empty)
                mapped_citations.append(cite)

    # Phase 2: If we didn't get any citations, or to ensure that relevant chunks
    # are always visible in the citations grid (making the source viewer functional),
    # add top retrieved search results that were either mentioned or high-score.
    for res in results:
        if res.chunk_id not in matched_ids:
            sec_num = res.metadata.section_number.lower().strip()
            art_num = res.metadata.article_number.lower().strip()
            
            # Clean up section prefix for matching
            sec_clean = sec_num.replace("section", "").strip()
            art_clean = art_num.replace("article", "").strip()

            mentioned = False
            if sec_clean and sec_clean in answer_text.lower():
                mentioned = True
            elif art_clean and art_clean in answer_text.lower():
                mentioned = True

            # Add if mentioned in text, or if it's one of the top 3 and we have few citations
            if mentioned or res.rank <= 3 or not mapped_citations:
                mapped_citations.append(Citation(
                    act_name=res.metadata.act_name,
                    section=res.metadata.section_number,
                    article=res.metadata.article_number,
                    chapter=res.metadata.chapter,
                    page=res.metadata.page_number,
                    quote=res.content,
                    relevance_score=res.score
                ))
                matched_ids.add(res.chunk_id)

    return mapped_citations


@router.post("/query", response_model=RAGResponse)
def query_endpoint(
    request: QueryRequest,
    query_rewriter=Depends(get_query_rewriter_dependency),
    hybrid_retriever: HybridRetriever = Depends(get_hybrid_retriever_dependency),
    reranker=Depends(get_reranker_dependency),
    answer_generator=Depends(get_answer_generator_dependency),
) -> RAGResponse:
    try:
        start_time = time.perf_counter()
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question must not be empty")
        rewritten_query = query_rewriter.rewrite(question) if request.rewrite_query else question
        results = hybrid_retriever.retrieve(
            query=rewritten_query,
            top_k=request.top_k,
            act_filter=request.act_filter,
            kb_id=request.kb_id,
            search_scope=request.search_scope,
            alpha=request.hybrid_alpha,
        )
        reranked = reranker.rerank(rewritten_query, results)
        context = format_context(reranked)
        rag_response = answer_generator.generate(
            question=question,
            context=context,
            rewritten_query=rewritten_query,
            temperature=request.temperature,
        )
        # Populate citation quotes and metadata from retrieved results
        rag_response.citations = map_citations_to_results(
            citations=rag_response.citations,
            results=reranked,
            answer_text=rag_response.answer
        )
        elapsed = (time.perf_counter() - start_time) * 1000
        rag_response.latency_ms = elapsed
        return rag_response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Query endpoint failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/retrieve", response_model=SearchResponse)
def retrieve_endpoint(
    request: SearchRequest,
    hybrid_retriever: HybridRetriever = Depends(get_hybrid_retriever_dependency),
    semantic_retriever: SemanticRetriever = Depends(get_semantic_retriever_dependency),
    bm25_retriever: BM25Retriever = Depends(get_bm25_retriever_dependency),
) -> SearchResponse:
    try:
        start_time = time.perf_counter()
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query must not be empty")
        if request.hybrid:
            results = hybrid_retriever.retrieve(
                query=request.query,
                top_k=request.top_k,
                act_filter=request.act_filter,
                chapter_filter=request.chapter_filter,
                kb_id=request.kb_id,
                search_scope=request.search_scope,
                alpha=request.hybrid_alpha,
            )
        else:
            results = semantic_retriever.retrieve(
                query=request.query,
                top_k=request.top_k,
                act_filter=request.act_filter,
                chapter_filter=request.chapter_filter,
                kb_id=request.kb_id,
                search_scope=request.search_scope,
            )
        elapsed = (time.perf_counter() - start_time) * 1000
        return SearchResponse(
            query=request.query,
            results=results,
            retrieval_method="hybrid" if request.hybrid else "semantic",
            total_results=len(results),
            latency_ms=elapsed,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Retrieve endpoint failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/filter", response_model=SearchResponse)
def filter_endpoint(
    act_name: str | None = None,
    chapter: str | None = None,
    section: str | None = None,
    kb_id: str = "global",
    semantic_retriever: SemanticRetriever = Depends(get_semantic_retriever_dependency),
) -> SearchResponse:
    try:
        start_time = time.perf_counter()
        if not act_name:
            raise HTTPException(status_code=400, detail="act_name is required")
        results = semantic_retriever.retrieve_by_metadata(
            act_name=act_name,
            chapter=chapter,
            section=section,
            kb_id=kb_id
        )
        elapsed = (time.perf_counter() - start_time) * 1000
        return SearchResponse(
            query="",
            results=results,
            retrieval_method="metadata",
            total_results=len(results),
            latency_ms=elapsed,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Filter endpoint failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stream")
def stream_endpoint(
    request: QueryRequest,
    query_rewriter=Depends(get_query_rewriter_dependency),
    hybrid_retriever: HybridRetriever = Depends(get_hybrid_retriever_dependency),
    reranker=Depends(get_reranker_dependency),
    answer_generator=Depends(get_answer_generator_dependency),
) -> StreamingResponse:
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question must not be empty")
        rewritten_query = query_rewriter.rewrite(question) if request.rewrite_query else question
        results = hybrid_retriever.retrieve(
            query=rewritten_query,
            top_k=request.top_k,
            act_filter=request.act_filter,
            kb_id=request.kb_id,
            search_scope=request.search_scope,
            alpha=request.hybrid_alpha,
        )
        reranked = reranker.rerank(rewritten_query, results)
        context = format_context(reranked)

        def event_stream() -> Generator[str, None, None]:
            gen = answer_generator.generate_stream(
                question=question,
                context=context,
                rewritten_query=rewritten_query,
                temperature=request.temperature,
            )
            rag_response = None
            try:
                while True:
                    token = next(gen)
                    yield f"data: {token}\n\n"
            except StopIteration as exc:
                # Capture final response returned by generator
                rag_response = exc.value
            except Exception as e:
                logger.error("Error in streaming response generation", error=str(e))
                yield f"data: \n[Generation error: {str(e)}]\n\n"
                return

            if rag_response:
                # Map citations to results
                mapped_citations = map_citations_to_results(
                    citations=rag_response.citations,
                    results=reranked,
                    answer_text=rag_response.answer
                )
                
                # Format final metadata payload
                metadata_payload = {
                    "citations": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in mapped_citations],
                    "rewritten_query": rewritten_query,
                    "model_used": rag_response.model_used
                }
                yield f"event: metadata\ndata: {json.dumps(metadata_payload)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Stream endpoint failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")
