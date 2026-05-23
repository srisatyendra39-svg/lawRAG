from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import List

from models.response_models import ChunkMetadata


@dataclass(frozen=True)
class LegalChunk:
    """Structured legal chunk with metadata and content counts."""

    chunk_id: str
    content: str
    raw_content: str
    metadata: ChunkMetadata
    char_count: int
    word_count: int


class LegalChunker:
    """Section-aware chunker for legal documents."""

    SECTION_MARKERS = ["Section ", "Article ", "CHAPTER ", "PART ", "Schedule "]

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, pages: List[object], source_file: str) -> List[LegalChunk]:
        """Chunk a document by pages and legal section boundaries."""
        chunks: List[LegalChunk] = []
        for page in pages:
            raw_text = page.text
            sections = self.section_aware_split(raw_text)
            if not sections:
                sections = [raw_text]
            for section in sections:
                if len(section) > self.chunk_size:
                    parts = self.overlap_split(section)
                else:
                    parts = [section.strip()]
                for raw_chunk in parts:
                    if not raw_chunk.strip():
                        continue
                    metadata = ChunkMetadata(
                        act_name="",
                        section_number="",
                        article_number="",
                        chapter="",
                        page_number=page.page_number,
                        source_file=source_file,
                    )
                    content = self.add_context_prefix(raw_chunk, metadata)
                    chunks.append(
                        LegalChunk(
                            chunk_id=str(uuid.uuid4()),
                            content=content,
                            raw_content=raw_chunk.strip(),
                            metadata=metadata,
                            char_count=len(raw_chunk),
                            word_count=len(raw_chunk.split()),
                        )
                    )
        return chunks

    def section_aware_split(self, text: str) -> List[str]:
        """Split text on legal markers, preserving the marker at the beginning of each chunk."""
        if not text:
            return []
        marker_regex = r"|".join(
            [
                r"Section\s+\d+[A-Za-z]?",
                r"Article\s+\d+[A-Za-z]?",
                r"CHAPTER\s+(?:[IVXivx]+|\d+)",
                r"PART\s+\d+",
                r"Schedule\s+\d+",
            ]
        )
        pattern = re.compile(rf"(?=(?:{marker_regex}))", flags=re.IGNORECASE)
        splits = [chunk.strip() for chunk in pattern.split(text) if chunk.strip()]
        return splits

    def overlap_split(self, text: str) -> List[str]:
        """Split text by overlapping windows while respecting sentence boundaries."""
        sentences = [s.strip() for s in re.split(r"(?<=[\.\?\!]\s)", text) if s.strip()]
        if not sentences:
            return []

        chunks: List[str] = []
        i = 0
        n = len(sentences)
        while i < n:
            current_chunk_sentences = []
            current_len = 0
            j = i
            while j < n:
                sent = sentences[j]
                sent_len = len(sent)
                if sent_len > self.chunk_size and current_len == 0:
                    step = max(self.chunk_size - self.chunk_overlap, 1)
                    for k in range(0, sent_len, step):
                        part = sent[k:k + self.chunk_size].strip()
                        if part:
                            chunks.append(part)
                    j += 1
                    break
                space_overhead = 1 if current_len > 0 else 0
                if current_len + space_overhead + sent_len <= self.chunk_size:
                    current_chunk_sentences.append(sent)
                    current_len += space_overhead + sent_len
                    j += 1
                else:
                    break

            if current_chunk_sentences:
                chunks.append(" ".join(current_chunk_sentences))

            if j >= n:
                break

            # Backtrack to create overlap for the next chunk
            next_start = j
            overlap_len = 0
            for k in range(j - 1, i, -1):
                sent_len = len(sentences[k])
                space_overhead = 1 if overlap_len > 0 else 0
                if overlap_len + space_overhead + sent_len <= self.chunk_overlap:
                    overlap_len += space_overhead + sent_len
                    next_start = k
                else:
                    break

            if next_start == i:
                i = j
            else:
                i = next_start

        return chunks

    def add_context_prefix(self, chunk: str, metadata: ChunkMetadata) -> str:
        """Prepend legal context metadata to a chunk to improve LLM understanding."""
        components = [metadata.act_name or "Unknown Act"]
        if metadata.chapter:
            components.append(metadata.chapter)
        if metadata.section_number:
            components.append(metadata.section_number)
        if metadata.article_number:
            components.append(metadata.article_number)
        if metadata.page_number:
            components.append(f"Page {metadata.page_number}")
        prefix = " | ".join(components)
        return f"[{prefix}]\n{chunk.strip()}"
