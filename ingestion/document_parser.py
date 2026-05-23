from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from ingestion.pdf_loader import PageContent, PDFLoader, PDFLoadError
from utils.logger import get_logger

logger = get_logger(__name__)


class DocumentParserError(Exception):
    """Raised when parsing fails."""
    pass


class DocumentParser:
    """Unified document parser supporting PDF, DOCX, and TXT."""

    def __init__(self, pdf_loader: PDFLoader | None = None) -> None:
        self.pdf_loader = pdf_loader or PDFLoader()

    def parse(self, file_path: Path) -> List[PageContent]:
        """Parse a file based on its extension and return PageContent list."""
        if not file_path.exists():
            raise DocumentParserError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()
        try:
            if suffix == ".pdf":
                return self.pdf_loader.load(file_path)
            elif suffix == ".docx":
                return self._parse_docx(file_path)
            elif suffix in (".txt", ".md"):
                return self._parse_txt(file_path)
            else:
                raise DocumentParserError(f"Unsupported file format: {suffix}")
        except Exception as exc:
            logger.error("Failed to parse document", file_path=str(file_path), error=str(exc))
            raise DocumentParserError(f"Error parsing document {file_path.name}: {exc}") from exc

    def _parse_docx(self, file_path: Path) -> List[PageContent]:
        """Extract text from DOCX file using standard library and create logical pages."""
        try:
            with zipfile.ZipFile(file_path) as docx:
                content_xml = docx.read("word/document.xml")
            
            tree = ET.fromstring(content_xml)
            # Define Namespace mapping
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            
            paragraphs = []
            for paragraph in tree.iter("{" + namespaces["w"] + "}p"):
                texts = [node.text for node in paragraph.iter("{" + namespaces["w"] + "}t") if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            
            full_text = "\n\n".join(paragraphs)
            return self._text_to_page_contents(full_text)
        except Exception as exc:
            raise DocumentParserError(f"Failed to extract DOCX XML text: {exc}") from exc

    def _parse_txt(self, file_path: Path) -> List[PageContent]:
        """Extract text from TXT file and create logical pages."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
                full_text = handle.read()
            return self._text_to_page_contents(full_text)
        except Exception as exc:
            raise DocumentParserError(f"Failed to read TXT file: {exc}") from exc

    def _text_to_page_contents(self, text: str, page_size: int = 2000) -> List[PageContent]:
        """Partition large block of text into sequential logical pages."""
        cleaned_text = re.sub(r"\s+", " ", text).strip()
        if not cleaned_text:
            raise DocumentParserError("Document is empty or contains only whitespace")

        # Partition text by page_size increments, aligning to sentence boundaries if possible
        sentences = [s.strip() for s in re.split(r"(?<=[\.\?\!]\s)", cleaned_text) if s.strip()]
        pages: List[PageContent] = []
        current_page_text: List[str] = []
        current_len = 0
        page_num = 1

        for sentence in sentences:
            sent_len = len(sentence)
            # If a single sentence exceeds the page size, split it directly
            if sent_len > page_size and not current_page_text:
                for k in range(0, sent_len, page_size):
                    chunk = sentence[k:k + page_size].strip()
                    if chunk:
                        pages.append(
                            PageContent(
                                page_number=page_num,
                                text=chunk,
                                word_count=len(chunk.split()),
                                char_count=len(chunk)
                            )
                        )
                        page_num += 1
                continue

            space_overhead = 1 if current_len > 0 else 0
            if current_len + space_overhead + sent_len <= page_size:
                current_page_text.append(sentence)
                current_len += space_overhead + sent_len
            else:
                # Flush current page
                page_text = " ".join(current_page_text)
                pages.append(
                    PageContent(
                        page_number=page_num,
                        text=page_text,
                        word_count=len(page_text.split()),
                        char_count=len(page_text)
                    )
                )
                page_num += 1
                # Start new page
                current_page_text = [sentence]
                current_len = sent_len

        # Flush remaining text
        if current_page_text:
            page_text = " ".join(current_page_text)
            pages.append(
                PageContent(
                    page_number=page_num,
                    text=page_text,
                    word_count=len(page_text.split()),
                    char_count=len(page_text)
                )
            )

        return pages
