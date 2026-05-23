from pathlib import Path

import fitz
import pytest

from chunking.legal_chunker import LegalChunker
from ingestion.metadata_extractor import LegalMetadataExtractor
from ingestion.pdf_loader import PDFLoadError, PDFLoader
from models.response_models import ChunkMetadata
from dataclasses import dataclass


def create_sample_pdf(path: Path, texts: list[str]) -> None:
    doc = fitz.open()
    for text in texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_load_pdf_returns_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_sample_pdf(pdf_path, ["Hello world", "Second page text"])
    loader = PDFLoader()
    pages = loader.load(pdf_path)
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2


def test_load_blank_pdf_raises_error(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()
    loader = PDFLoader()
    with pytest.raises(PDFLoadError):
        loader.load(pdf_path)


def test_page_count_matches(tmp_path: Path) -> None:
    pdf_path = tmp_path / "count.pdf"
    create_sample_pdf(pdf_path, ["Page one", "Page two", "Page three"])
    loader = PDFLoader()
    pages = loader.load(pdf_path)
    assert len(pages) == 3


def test_section_aware_split() -> None:
    chunker = LegalChunker(chunk_size=50, chunk_overlap=10)
    text = "Section 1 This is section one. Article 2 This is article two."
    splits = chunker.section_aware_split(text)
    assert len(splits) == 2
    assert splits[0].startswith("Section 1")
    assert splits[1].startswith("Article 2")


def test_metadata_preserved_in_chunks() -> None:
    extractor = LegalMetadataExtractor()
    metadata = extractor.extract("Section 43A of the Act.", page_number=5, source_file="IT_Act_2000.pdf")
    assert metadata.act_name == "Information Technology Act, 2000"
    assert metadata.section_number == "Section 43A"
    assert metadata.page_number == 5
