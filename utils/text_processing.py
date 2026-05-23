from __future__ import annotations

import re
from typing import Dict, List
from models.response_models import SearchResult, Citation

def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase, removing non-alphanumeric characters, and collapsing whitespace."""
    if not text:
        return ""
    text = text.lower()
    # Replace non-alphanumeric with spaces, then collapse multiple spaces
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_overlap_ratio(text1: str, text2: str) -> float:
    """Compute the Szymkiewicz-Simpson overlap coefficient between two strings."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    if not norm1 or not norm2:
        return 0.0
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    min_size = min(len(words1), len(words2))
    return len(intersection) / min_size

def deduplicate_results(results: List[SearchResult], overlap_threshold: float = 0.75) -> List[SearchResult]:
    """Deduplicate search results by chunk_id and content overlap, keeping the highest score."""
    # First, deduplicate by chunk_id (keeping the highest score)
    seen_ids: Dict[str, SearchResult] = {}
    for result in results:
        existing = seen_ids.get(result.chunk_id)
        if existing is None or result.score > existing.score:
            seen_ids[result.chunk_id] = result
    
    # Sort them by score descending to ensure we process the highest-ranked ones first
    sorted_unique_id = sorted(seen_ids.values(), key=lambda r: r.score, reverse=True)
    
    # Now deduplicate by semantic/overlap threshold
    deduplicated: List[SearchResult] = []
    for result in sorted_unique_id:
        is_duplicate = False
        for accepted in deduplicated:
            if get_overlap_ratio(result.content, accepted.content) >= overlap_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            deduplicated.append(result)
    return deduplicated

def clean_repeated_sentences(text: str) -> str:
    """Post-process answer text to remove repeated paragraphs and repeated sentences."""
    if not text:
        return ""
    
    # First, clean citations section if present
    text = clean_citations_section(text)
    
    # Split text into paragraphs
    paragraphs = text.split("\n\n")
    cleaned_paragraphs = []
    
    for para in paragraphs:
        para_strip = para.strip()
        if not para_strip:
            continue
        
        # Check if the paragraph is a citations header or marker block, preserve it
        if "CITATIONS:" in para_strip or "---" in para_strip:
            cleaned_paragraphs.append(para_strip)
            continue
            
        is_para_duplicate = False
        for accepted_para in cleaned_paragraphs:
            if "CITATIONS:" in accepted_para or "---" in accepted_para:
                continue
            if get_overlap_ratio(para_strip, accepted_para) >= 0.80:
                is_para_duplicate = True
                break
        if is_para_duplicate:
            continue
            
        # Deduplicate sentences within the paragraph
        sentences = re.split(r"(?<=[\.\?\!])\s+", para_strip)
        cleaned_sentences = []
        for sentence in sentences:
            sentence_strip = sentence.strip()
            if not sentence_strip:
                continue
            
            is_sent_duplicate = False
            for accepted_sent in cleaned_sentences:
                # If they are very short (e.g., "Yes.", "No."), don't count as duplicate unless exact match
                if len(sentence_strip.split()) < 4:
                    if sentence_strip.lower() == accepted_sent.lower():
                        is_sent_duplicate = True
                        break
                else:
                    if get_overlap_ratio(sentence_strip, accepted_sent) >= 0.80:
                        is_sent_duplicate = True
                        break
            if not is_sent_duplicate:
                cleaned_sentences.append(sentence_strip)
        
        if cleaned_sentences:
            cleaned_paragraphs.append(" ".join(cleaned_sentences))
            
    return "\n\n".join(cleaned_paragraphs)

def clean_citations_section(text: str) -> str:
    """Deduplicate bullet points in the CITATIONS section of the text."""
    if "CITATIONS:" not in text:
        return text
    
    parts = re.split(r"(CITATIONS:)", text, flags=re.IGNORECASE)
    if len(parts) < 3:
        return text
        
    before = parts[0]
    citations_header = parts[1]
    after = "".join(parts[2:])
    
    subparts = re.split(r"(---)", after)
    citations_content = subparts[0]
    remainder = "".join(subparts[1:])
    
    lines = citations_content.split("\n")
    seen_bullets = set()
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        if any(stripped.startswith(char) for char in ["•", "*", "-"]):
            norm_bullet = re.sub(r"[^a-zA-Z0-9]+", "", stripped).lower()
            if norm_bullet not in seen_bullets:
                seen_bullets.add(norm_bullet)
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)
            
    new_citations_content = "\n".join(cleaned_lines)
    return before + citations_header + new_citations_content + remainder

def deduplicate_citations(citations: List[Citation]) -> List[Citation]:
    """Remove duplicate citations from the list, preserving order."""
    seen = set()
    unique_citations = []
    for c in citations:
        key = (
            c.act_name.lower().strip(),
            c.section.lower().strip(),
            c.article.lower().strip(),
            c.chapter.lower().strip(),
            c.page,
        )
        if key not in seen:
            seen.add(key)
            unique_citations.append(c)
    return unique_citations
