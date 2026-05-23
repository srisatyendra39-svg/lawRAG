from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

from models.response_models import ChunkMetadata


class LegalMetadataExtractor:
    """Extract structured legal metadata from PDF text chunks."""

    SECTION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"(?i)section\s+(\d+[A-Za-z]?)(?![A-Za-z0-9])")
    ARTICLE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"(?i)article\s+(\d+[A-Za-z]?)(?![A-Za-z0-9])")
    CHAPTER_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"(?i)chapter\s+((?:[IVXivx]+|\d+))[\.\s\-—]?")
    SUBSECTION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\((\d+)\)\s")

    def __init__(self, act_mappings: dict[str, str] | None = None) -> None:
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
                }
        else:
            self.act_mappings = act_mappings

    def extract(self, text: str, page_number: int, source_file: str) -> ChunkMetadata:
        """Extract act-level metadata from a chunk of legal text."""
        act_name = self._detect_act(source_file)
        section_number = self._find_section(text)
        article_number = self._find_article(text)
        chapter = self._find_chapter(text)
        return ChunkMetadata(
            act_name=act_name,
            section_number=section_number,
            article_number=article_number,
            chapter=chapter,
            page_number=page_number,
            source_file=Path(source_file).name,
        )

    def _detect_act(self, source_file: str) -> str:
        name = source_file.lower()
        for substring, act in self.act_mappings.items():
            if substring in name:
                return act
        return "Unknown Act"

    def _find_section(self, text: str) -> str:
        match = self.SECTION_PATTERN.search(text)
        if match:
            return f"Section {match.group(1).strip()}"
        return ""

    def _find_article(self, text: str) -> str:
        match = self.ARTICLE_PATTERN.search(text)
        if match:
            return f"Article {match.group(1).strip()}"
        return ""

    def _find_chapter(self, text: str) -> str:
        match = self.CHAPTER_PATTERN.search(text)
        if match:
            value = match.group(1).strip()
            return f"Chapter {value}" if not value.lower().startswith("chapter") else value
        return ""
