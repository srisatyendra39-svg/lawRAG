from __future__ import annotations

from pathlib import Path

from ingestion.pipeline import build_ingestion_pipeline
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Run ingestion over all PDFs in the raw data directory."""
    pipeline = build_ingestion_pipeline()
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_dir}")
    results = pipeline.ingest_all_documents(raw_dir)
    for result in results:
        logger.info(
            "Ingestion result",
            act_name=result.act_name,
            status=result.status,
            chunks_created=result.chunks_created,
            processing_time_ms=result.processing_time_ms,
        )
    print("Ingestion complete")


if __name__ == "__main__":
    main()
