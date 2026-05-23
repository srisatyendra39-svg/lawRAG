from __future__ import annotations

import pytest
from models.response_models import SearchResult, ChunkMetadata, Citation
from utils.text_processing import (
    normalize_text,
    get_overlap_ratio,
    deduplicate_results,
    clean_repeated_sentences,
    deduplicate_citations,
)

def test_normalize_text() -> None:
    text = "  Hello, World!!! This is Section 43A of the IT Act.   "
    assert normalize_text(text) == "hello world this is section 43a of the it act"

def test_get_overlap_ratio() -> None:
    text1 = "This is a legal document chunk about data protection."
    text2 = "This is a legal document chunk about data protection in India."
    # Both are very similar
    ratio = get_overlap_ratio(text1, text2)
    assert ratio > 0.8

    text3 = "Completely unrelated text concerning the constitution of India and president roles."
    ratio2 = get_overlap_ratio(text1, text3)
    assert ratio2 < 0.3

def test_deduplicate_results() -> None:
    meta = ChunkMetadata(
        act_name="IT Act",
        section_number="43A",
        article_number="",
        chapter="Chapter XI",
        page_number=1,
        source_file="it.pdf",
        kb_id="global",
        doc_category="global"
    )

    results = [
        SearchResult(
            chunk_id="chunk_1",
            content="This is the first section detail about data privacy and penalty.",
            score=0.9,
            metadata=meta,
            rank=1
        ),
        SearchResult(
            chunk_id="chunk_2",
            content="This is the first section detail about data privacy and penalty.", # Exact same text, diff chunk_id
            score=0.85,
            metadata=meta,
            rank=2
        ),
        SearchResult(
            chunk_id="chunk_1", # Same chunk_id, lower score
            content="Some other text.",
            score=0.7,
            metadata=meta,
            rank=3
        ),
        SearchResult(
            chunk_id="chunk_3",
            content="This is the first section detail about data privacy and penalty with minor additions.", # Near duplicate (>75% overlap)
            score=0.8,
            metadata=meta,
            rank=4
        ),
        SearchResult(
            chunk_id="chunk_4",
            content="Completely different topic about cyber security offenses.",
            score=0.75,
            metadata=meta,
            rank=5
        ),
    ]

    deduped = deduplicate_results(results, overlap_threshold=0.75)
    # Should keep chunk_1 (highest score 0.9) and chunk_4. Others are duplicates.
    assert len(deduped) == 2
    chunk_ids = {r.chunk_id for r in deduped}
    assert "chunk_1" in chunk_ids
    assert "chunk_4" in chunk_ids

def test_clean_repeated_sentences() -> None:
    text = (
        "Section 43A provides for compensation for failure to protect data. "
        "Section 43A provides for compensation for failure to protect data. " # Repeated sentence
        "If a body corporate is negligent in implementing reasonable security practices, it shall be liable.\n\n"
        "Section 43A provides for compensation for failure to protect data. " # Repeated paragraph (near duplicate)
        "If a body corporate is negligent in implementing reasonable security practices, it shall be liable."
    )
    cleaned = clean_repeated_sentences(text)
    assert "Section 43A provides for compensation" in cleaned
    # Check that it only has one instance of the paragraph and sentence
    assert cleaned.count("Section 43A provides for compensation") == 1

def test_clean_citations_section() -> None:
    text = (
        "The court ruled that privacy is a fundamental right.\n\n"
        "--- CITATIONS:\n"
        "• [Constitution of India - Article 21, Page 10]\n"
        "• [Constitution of India - Article 21, Page 10]\n" # Repeated citation
        "• [IT Act - Section 43A, Page 5]\n"
        "---"
    )
    cleaned = clean_repeated_sentences(text)
    assert cleaned.count("Article 21") == 1
    assert cleaned.count("Section 43A") == 1

def test_deduplicate_citations() -> None:
    citations = [
        Citation(act_name="IT Act", section="43A", article="", chapter="", page=12, quote=""),
        Citation(act_name="IT Act", section="43a ", article="", chapter="", page=12, quote=""), # case & space variant
        Citation(act_name="Constitution", section="", article="21", chapter="", page=45, quote=""),
    ]
    deduped = deduplicate_citations(citations)
    assert len(deduped) == 2
    assert deduped[0].act_name == "IT Act"
    assert deduped[1].act_name == "Constitution"
