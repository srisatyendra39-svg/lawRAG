from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import fitz
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFLoadError(Exception):
    """Raised when a PDF cannot be loaded or parsed."""


@dataclass(frozen=True)
class PageContent:
    """Structured content extracted from a single PDF page."""

    page_number: int
    text: str
    word_count: int
    char_count: int


class PDFLoader:
    """Loader for PDF documents that preserves page boundaries and metadata."""

    BLANK_PAGE_THRESHOLD = 1
    CLEANUP_PATTERN = re.compile(r"[\u200b\u200c\u200d\xa0]+")

    def load(self, file_path: Path) -> list[PageContent]:
        """Load a PDF and return page-level content with counts."""
        if not file_path.exists():
            raise PDFLoadError(f"PDF file not found: {file_path}")

        try:
            document = fitz.open(file_path)
        except Exception as exc:
            raise PDFLoadError(f"Failed to open PDF: {file_path}") from exc

        result: list[PageContent] = []
        total_words = 0
        total_chars = 0
        total_pages = document.page_count

        for page_number in range(total_pages):
            page_index = page_number + 1
            text = self._extract_page_text(document, page_number)
            cleaned = self._clean_text(text)
            if len(cleaned) < self.BLANK_PAGE_THRESHOLD:
                logger.debug("Skipping blank or nearly blank page", page_number=page_index)
                continue
            word_count = len(cleaned.split())
            char_count = len(cleaned)
            total_words += word_count
            total_chars += char_count
            if page_index % 10 == 0:
                logger.info("Loaded PDF pages", page_number=page_index, total_pages=total_pages)
            result.append(PageContent(page_number=page_index, text=cleaned, word_count=word_count, char_count=char_count))

        if not result:
            raise PDFLoadError(f"PDF appears empty or contained only blank pages: {file_path}")

        logger.info(
            "PDF loaded",
            file_path=str(file_path),
            total_pages=total_pages,
            total_words=total_words,
            total_chars=total_chars,
            extracted_pages=len(result),
        )
        return result

    def _extract_page_text(self, document: fitz.Document, page_index: int) -> str:
        """Extract text from a specific PDF page, handling scanning warnings."""
        try:
            page = document.load_page(page_index)
            text = page.get_text("text")
            if not text.strip():
                logger.warning("Page appears empty or scanned; no text extracted", page_index=page_index)
            return text
        except Exception as exc:
            raise PDFLoadError(f"Unable to extract page {page_index + 1}") from exc

    def _clean_text(self, text: str) -> str:
        """Clean extracted text by normalizing whitespace and removing control characters."""
        cleaned = self.CLEANUP_PATTERN.sub(" ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
