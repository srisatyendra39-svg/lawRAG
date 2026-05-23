from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_reranker_dependency, get_settings_dependency
from configs.settings import Settings
from models.request_models import EvaluationRequest
from models.response_models import EvaluationResult
from rerankers.cross_encoder_reranker import CrossEncoderReranker
from evaluation.ragas_evaluator import LegalRAGEvaluator
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/evaluate", tags=["Evaluation"])


@router.post("/run", response_model=EvaluationResult)
def run_evaluation(
    request: EvaluationRequest,
    reranker: CrossEncoderReranker = Depends(get_reranker_dependency),
    settings: Settings = Depends(get_settings_dependency),
) -> EvaluationResult:
    evaluator = LegalRAGEvaluator(
        reranker=reranker,
        ollama_base_url=settings.ollama_base_url,
        model_name=settings.ollama_model,
    )
    contexts = ["" for _ in request.questions]
    results = evaluator.evaluate(request.questions, contexts, request.ground_truths)
    output_file = Path("data/evaluation_results.json")
    evaluator.save_results(results, output_file)
    return results


@router.get("/results")
def get_evaluation_results() -> dict[str, object]:
    path = Path("data/evaluation_results.json")
    if not path.exists():
        raise HTTPException(status_code=404, detail="No evaluation results found")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data
