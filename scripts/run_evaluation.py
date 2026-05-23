from __future__ import annotations

from pathlib import Path

from evaluation.ragas_evaluator import LegalRAGEvaluator
from rerankers.cross_encoder_reranker import get_reranker
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    reranker = get_reranker()
    evaluator = LegalRAGEvaluator(
        reranker=reranker,
        ollama_base_url="http://localhost:11434",
        model_name="llama3",
    )

    questions = [
        "What are the penalties under Section 43 of the Information Technology Act, 2000?",
        "What does Article 21 of the Constitution of India say about the right to life?",
        "How does the Digital Personal Data Protection Act, 2023 define personal data?",
    ]
    contexts = [
        "Sample legal context from IT Act Section 43.",
        "Sample legal context from Constitution Article 21.",
        "Sample legal context from DPDP Act personal data definition.",
    ]

    results = evaluator.evaluate(questions=questions, contexts=contexts)
    output_file = Path("data/evaluation_results.json")
    evaluator.save_results(results, output_file)
    report = evaluator.generate_report(results)
    print(report)
    logger.info("Evaluation run complete", output=str(output_file))


if __name__ == "__main__":
    main()
