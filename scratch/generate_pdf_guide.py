import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # First page is the cover page, draw background accents but no header/footer text
            self.saveState()
            # Draw elegant gold sidebar
            self.setFillColor(colors.HexColor("#C5A55A"))
            self.rect(0, 0, 30, 792, fill=True, stroke=False)
            self.setFillColor(colors.HexColor("#1A2B4C"))
            self.rect(30, 0, 10, 792, fill=True, stroke=False)
            self.restoreState()
            return

        self.saveState()
        
        # Color Palette
        primary_color = colors.HexColor("#1A2B4C")
        gold_color = colors.HexColor("#C5A55A")
        muted_color = colors.HexColor("#7A7A6C")
        border_color = colors.HexColor("#E5E5E5")
        
        # Running Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(primary_color)
        self.drawString(54, 750, "LAWRAG")
        self.setFont("Helvetica", 8)
        self.setFillColor(muted_color)
        self.drawString(100, 750, "|   AI-Powered Indian Legal Research Assistant Guide")
        
        self.setStrokeColor(border_color)
        self.setLineWidth(0.5)
        self.line(54, 742, 558, 742)
        
        # Running Footer
        self.line(54, 55, 558, 55)
        self.setFont("Helvetica", 8)
        self.drawString(54, 40, "Confidential   •   Architectural Reference & Interview Prep Manual")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_str)
        
        # Running sidebar accents
        self.setFillColor(gold_color)
        self.rect(0, 0, 6, 792, fill=True, stroke=False)
        
        self.restoreState()

def create_pdf(output_path):
    # Setup document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=80,
        bottomMargin=80
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette Colors
    c_primary = colors.HexColor("#1A2B4C")   # Navy/Slate
    c_secondary = colors.HexColor("#4A4A3E") # Charcoal
    c_gold = colors.HexColor("#C5A55A")      # Muted Gold
    c_gold_dark = colors.HexColor("#8B6F2E") # Deep Gold
    c_muted = colors.HexColor("#7A7A6C")     # Olive Muted Gray
    c_light_bg = colors.HexColor("#F8F9FA")  # Off-white
    c_code_bg = colors.HexColor("#F1F3F5")   # Code block gray
    
    # Custom Typography Styles
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=30,
        leading=38,
        textColor=c_primary,
        spaceAfter=15
    )
    
    style_cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=c_muted,
        spaceAfter=40
    )
    
    style_cover_meta = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=c_gold_dark,
        spaceAfter=4
    )
    
    style_h1 = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceBefore=18,
        spaceAfter=10,
        keepWithNext=True
    )
    
    style_h2 = ParagraphStyle(
        'Header2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_gold_dark,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    style_body = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14.5,
        textColor=c_secondary,
        spaceAfter=8
    )
    
    style_bullet = ParagraphStyle(
        'BulletCustom',
        parent=style_body,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    style_code = ParagraphStyle(
        'CodeCustom',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#2B2B2B"),
        backColor=c_code_bg,
        borderColor=colors.HexColor("#E0E0E0"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=8
    )
    
    style_qa_q = ParagraphStyle(
        'QAQuestion',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    style_qa_a = ParagraphStyle(
        'QAAnswer',
        parent=style_body,
        leftIndent=10,
        spaceAfter=12
    )

    story = []

    # ══════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════
    story.append(Spacer(1, 100))
    # Elegant category/badge
    story.append(Paragraph("<font color='#C5A55A'><b>ARCHITECTURAL BLUEPRINT & INTERVIEW REFERENCE</b></font>", ParagraphStyle('Badge', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12, spaceAfter=20)))
    
    # Title
    story.append(Paragraph("LawRAG", style_cover_title))
    # Elegant divider line
    d_table = Table([[""]], colWidths=[380], rowHeights=[3])
    d_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_gold),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(d_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Production-Grade, Local & Offline Indian Legal Q&A Assistant<br/>A Comprehensive End-to-End RAG System Implementation Guide", style_cover_subtitle))
    
    story.append(Spacer(1, 120))
    
    # Metadata Box
    story.append(Paragraph("AUTHOR & ARCHITECT", style_cover_meta))
    story.append(Paragraph("AI Coding Agent (Antigravity)", style_body))
    story.append(Spacer(1, 10))
    story.append(Paragraph("SYSTEM TECHNOLOGY STACK", style_cover_meta))
    story.append(Paragraph("FastAPI  •  ChromaDB  •  Ollama (llama3)  •  BM25  •  Cross-Encoder Reranker  •  SentenceTransformers", style_body))
    story.append(Spacer(1, 10))
    story.append(Paragraph("DOCUMENT DATE", style_cover_meta))
    story.append(Paragraph("May 2026", style_body))
    
    story.append(PageBreak())

    # ══════════════════════════════════════════════
    # SECTION 1: EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════
    story.append(Paragraph("1. Executive Summary", style_h1))
    story.append(Paragraph(
        "<b>LawRAG</b> is a high-performance, domain-specific Retrieval-Augmented Generation (RAG) system designed "
        "to deliver accurate, context-grounded Q&A for Indian Legislation (such as the Information Technology Act, 2000 "
        "and the Digital Personal Data Protection Act, 2023). It solves a major challenge in domain-specific AI: "
        "providing absolute safety, reliability, and precision without transmitting sensitive data outside local networks.",
        style_body
    ))
    story.append(Paragraph(
        "To achieve this, the system is architected as a fully local, <b>100% offline-capable</b> application. It leverages "
        "advanced retrieval pipelines, specifically merging dense semantic search (ChromaDB Vector Store) with sparse keyword search "
        "(Rank-BM25), reranking results via a neural cross-encoder model, and generating final answers using a localized "
        "Large Language Model (Ollama's llama3 model). Special provisions have been built in to handle cold-start latencies and LLM timeouts, "
        "guaranteeing a robust fallback mechanism that serves offline context if the model is unreachable.",
        style_body
    ))
    
    # Highlight box (Table)
    summary_box_data = [[
        Paragraph(
            "<b>Key Features of the System:</b><br/>"
            "• <b>Dual Retrieval System:</b> Merges lexical precision (BM25) with deep conceptual understanding (Semantic Embeddings).<br/>"
            "• <b>Neural Reranking:</b> Re-scores documents using a Cross-Encoder to optimize context relevance.<br/>"
            "• <b>Domain-Specific Chunking:</b> Sections are split using statutory structural boundary parsing rather than arbitrary token counts.<br/>"
            "• <b>Guaranteed Availability Fallback:</b> Automatically creates structural answers directly from search results if the LLM fails.<br/>"
            "• <b>Zero Data Leakage:</b> Runs locally with cached Hugging Face models using <font face='Courier'>HF_HUB_OFFLINE='1'</font>.",
            style_body
        )
    ]]
    summary_box = Table(summary_box_data, colWidths=[480])
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F6F9")),
        ('BORDER', (0,0), (-1,-1), 1, c_gold),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(summary_box)
    story.append(Spacer(1, 15))

    # ══════════════════════════════════════════════
    # SECTION 2: SYSTEM ARCHITECTURE
    # ══════════════════════════════════════════════
    story.append(Paragraph("2. System Architecture & Information Flow", style_h1))
    story.append(Paragraph(
        "The system separates core concerns into three distinct layers: a FastAPI Backend Server, an Offline Data Ingestion Pipeline, "
        "and a premium Vanilla HTML/CSS/JS Frontend Portal.",
        style_body
    ))
    
    # Textual Flow diagram
    story.append(Paragraph("<b>The 8-Step Information Flow:</b>", style_h2))
    flow_steps = [
        "<b>1. Query Reception & Security:</b> The frontend issues a POST query containing the question and search settings to the FastAPI endpoint <font face='Courier'>/api/v1/search/query</font>. The request is authenticated using API Key header verification (<font face='Courier'>X-API-Key</font>).",
        "<b>2. Query Rewriting / Expansion:</b> To improve recall, the Query Rewriter feeds the raw user prompt to a local llama3 model (via Ollama) to output a structurally expanded query containing acts, legal synonyms, and target sections.",
        "<b>3. Dual Retrieval Extraction:</b> The rewritten query is sent in parallel to: (a) <i>Dense Retriever</i> (ChromaDB querying cached sentence-transformers embeddings) and (b) <i>Sparse Retriever</i> (Rank-BM25 matching query tokens against indexed text).",
        "<b>4. Hybrid Fusion:</b> The dense scores and sparse scores are fused using convex combination scaling with a tunable ratio (<font face='Courier'>alpha=0.7</font>) prioritizing semantic density while ensuring keyword matches aren't missed.",
        "<b>5. Cross-Encoder Reranking:</b> The top retrieved candidate chunks are fed into a Cross-Encoder neural network (<font face='Courier'>ms-marco-MiniLM-L-6-v2</font>), which performs joint query-document attention scoring to return the top 5 highly relevant text passages.",
        "<b>6. Prompt Assembly:</b> The retrieved context is formatted into a strict prompt wrapper. The prompt instructs the LLM to only answer utilizing the provided context, preventing hallucination.",
        "<b>7. Response Generation & Fallback:</b> The prompt is sent to Ollama's local chat API. If the Ollama client fails or times out (exceeding our 180s threshold), the Answer Generator catches the error and executes a deterministic fallback, creating an organized answer structure directly from the search context.",
        "<b>8. Citation Mapping:</b> The Citation Mapper aligns the generated LLM text with the retrieved vector metadata. It parses the references and highlights exact matching sources (Act Name, Section, Page, Relevance Score) in the frontend grid."
    ]
    for step in flow_steps:
        story.append(Paragraph(step, style_bullet))
        
    story.append(Spacer(1, 10))
    story.append(PageBreak())

    # ══════════════════════════════════════════════
    # SECTION 3: INGESTION PIPELINE
    # ══════════════════════════════════════════════
    story.append(Paragraph("3. Ingestion Pipeline & PDF Parser", style_h1))
    story.append(Paragraph(
        "The offline ingestion controller orchestrates data ingestion from raw files directly to vector database collections.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Key Files involved:</b><br/>"
        "• <a href='file:///c:/Users/srisa/OneDrive/Desktop/law-rag/legal-rag-assistant/ingestion/pipeline.py'>ingestion/pipeline.py</a>: Orchestrates loaders, parsers, and vector stores.<br/>"
        "• <a href='file:///c:/Users/srisa/OneDrive/Desktop/law-rag/legal-rag-assistant/ingestion/pdf_loader.py'>ingestion/pdf_loader.py</a>: Handles raw bytes extraction using PyMuPDF (fitz).",
        style_body
    ))
    story.append(Paragraph(
        "<b>PyMuPDF Extraction Rationale:</b> PyMuPDF is chosen over generic PDF extraction engines because it provides extremely "
        "fast access to document bounding boxes, fonts, headers, footers, and physical page dividers. This allows the parser "
        "to record exact page numbers for every extracted chunk, ensuring citations are auditable.",
        style_body
    ))
    
    # Code snippet or pseudocode
    story.append(Paragraph("<b>Ingestion Implementation Structure:</b>", style_h2))
    story.append(Paragraph(
        "class IngestionPipeline:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;def ingest_file(self, file_path, kb_id, act_name, overwrite):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 1. Parse PDF pages to structured records<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;documents = self.parser.parse(file_path)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 2. Extract and assign metadata (Acts/Sections/Chapters)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;documents = self.metadata_extractor.enrich(documents, act_name)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 3. Split documents into legal-aware chunks<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;chunks = self.chunker.split_documents(documents)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 4. Insert/Upsert into ChromaDB collections<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.vector_store.add_chunks(chunks, kb_id, overwrite)",
        style_code
    ))

    # ══════════════════════════════════════════════
    # SECTION 4: METADATA EXTRACTION
    # ══════════════════════════════════════════════
    story.append(Paragraph("4. Legal Metadata Extraction & Scope Filters", style_h1))
    story.append(Paragraph(
        "Legal texts are highly structured. Rather than relying on LLMs to guess the origin of a clause, LawRAG "
        "extracts rich metadata at ingestion time using highly optimized regular expressions.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Attributes Captured:</b><br/>"
        "• <b>Act Name:</b> Maps raw files to target legislations (e.g. 'Information Technology Act, 2000').<br/>"
        "• <b>Section/Article:</b> Parses section markers (e.g. 'Section 43A', 'Article 21') to assign exact numbering.<br/>"
        "• <b>Chapter:</b> Detects chapter divisions (e.g. 'Chapter II: Digital Signatures').<br/>"
        "• <b>Page Number:</b> Records the precise physical page inside the source document.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Search Scope Boundaries:</b> The system supports three query scopes: <i>Global</i> (searches all indexed files), "
        "<i>Custom KB</i> (isolates searches to specific client directories or knowledge bases), and <i>Combined</i> (searches both "
        "global and client databases). Scope isolation is achieved programmatically by passing collection metadata filters into ChromaDB queries.",
        style_body
    ))
    story.append(Spacer(1, 10))
    story.append(PageBreak())

    # ══════════════════════════════════════════════
    # SECTION 5: CHUNKING STRATEGY
    # ══════════════════════════════════════════════
    story.append(Paragraph("5. Domain-Specific Legal Chunking Strategy", style_h1))
    story.append(Paragraph(
        "Traditional RAG pipelines rely on character-count or token-count based chunking (e.g., recursive splitting "
        "at 500 characters with a 50-character overlap). While simple, this approach is destructive for legal documents, "
        "often splitting a single statutory section in half, severing critical conditional clauses (like 'provided that...') "
        "from the main provision.",
        style_body
    ))
    story.append(Paragraph(
        "<b>LawRAG's Solution: Section-Based Semantic Chunking</b><br/>"
        "We implement a legal-aware chunker (<a href='file:///c:/Users/srisa/OneDrive/Desktop/law-rag/legal-rag-assistant/chunking/legal_chunker.py'>chunking/legal_chunker.py</a>) "
        "which uses custom boundary rules:<br/>"
        "1. It scans text for legislative section and article headers (e.g., 'Section 43A:', 'Section 66A:').<br/>"
        "2. It defines chunk boundaries exactly at section start positions.<br/>"
        "3. Chunks are allowed to grow to include the full text of a section. Overlap is placed carefully to ensure that "
        "preceding section definitions or act names are prepended to downstream clauses, preserving context completeness.",
        style_body
    ))

    # ══════════════════════════════════════════════
    # SECTION 6: HYBRID RETRIEVAL
    # ══════════════════════════════════════════════
    story.append(Paragraph("6. Hybrid Retrieval System (Lexical + Semantic)", style_h1))
    story.append(Paragraph(
        "Dense semantic retrieval using vector embeddings often struggles with exact code-word searches, such as searching "
        "for 'Section 43A' or specific technical acronyms like 'IT Act'. On the other hand, keyword-based search (BM25) "
        "fails to resolve synonyms or conceptual matches. LawRAG implements a robust <b>Hybrid Retriever</b> to combine "
        "the best of both worlds.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Math of Score Fusion:</b><br/>"
        "For a query, we retrieve the top <i>K</i> documents from the Dense semantic index and BM25 index. Scores are normalized "
        "to a 0-1 scale. The final ranking score for each document is computed as:<br/>"
        "<b>Score = (alpha * SemanticScore) + ((1 - alpha) * BM25Score)</b><br/>"
        "Where <b>alpha = 0.7</b> is the default blend parameter favoring conceptual alignment while preserving keyword relevance.",
        style_body
    ))
    
    # ══════════════════════════════════════════════
    # SECTION 7: NEURAL RERANKING
    # ═══════════════════════════════════════
    story.append(Paragraph("7. Neural Reranking Engine", style_h1))
    story.append(Paragraph(
        "While hybrid retrieval is highly efficient at narrowing down thousands of pages to 15-20 candidates, it relies "
        "on Bi-Encoder networks (where document embeddings and query embeddings are generated independently). Bi-encoders "
        "cannot model complex token-level cross-attention between queries and documents.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Cross-Encoder Mechanics:</b><br/>"
        "LawRAG feeds the top 15 candidate chunks into a Cross-Encoder model (<font face='Courier'>ms-marco-MiniLM-L-6-v2</font>). "
        "The Cross-Encoder takes both the query and document as a unified single input string, allowing the self-attention "
        "layers to compare every query token directly against every document token. This outputs a highly accurate "
        "relevance score, reranking the best 5 context chunks to feed into the LLM prompt.",
        style_body
    ))
    story.append(Spacer(1, 10))
    story.append(PageBreak())

    # ══════════════════════════════════════════════
    # SECTION 8: QUERY REWRITER
    # ══════════════════════════════════════════════
    story.append(Paragraph("8. Query Rewriting and Expansion", style_h1))
    story.append(Paragraph(
        "Users frequently ask questions in natural language which lack statutory precision (e.g. asking 'Can I get fined for data leak?' "
        "instead of 'What is the liability for data protection negligence under Section 43A of the IT Act?').",
        style_body
    ))
    story.append(Paragraph(
        "<b>Query Expansion Logic:</b><br/>"
        "The Query Rewriter (<a href='file:///c:/Users/srisa/OneDrive/Desktop/law-rag/legal-rag-assistant/generators/query_rewriter.py'>generators/query_rewriter.py</a>) "
        "passes the user question to the local LLM with a specialized system instruction. The model expands the query, translating "
        "common phrasing to legal terminology. For example, our test query <i>'What is Section 43A of the IT Act?'</i> was expanded to:<br/>"
        "<i>'What are the provisions and implications of Section 43A of the Information Technology Act, 2000, regarding compensation for non-compliance with security standards?'</i><br/>"
        "This drastically improves retrieval recall because the expanded tokens match both the dense embedding vectors and sparse BM25 indices.",
        style_body
    ))

    # ══════════════════════════════════════════════
    # SECTION 9: GENERATION & TIMEOUT FALLBACK
    # ══════════════════════════════════════════════
    story.append(Paragraph("9. LLM Response Generation & Availability Fallbacks", style_h1))
    story.append(Paragraph(
        "RAG applications running locally on CPU or mid-range GPUs suffer from cold-start latency when loading LLM weights, "
        "often causing client connections to time out. LawRAG implements two major optimizations to handle this:",
        style_body
    ))
    story.append(Paragraph(
        "<b>1. Timeout Extension:</b> The connection-pooled Ollama client timeout was increased to 180 seconds. This allows "
        "sufficient margin for the local GPU/CPU to load the `llama3` model and generate tokens without interrupting the client request.",
        style_body
    ))
    story.append(Paragraph(
        "<b>2. Deterministic Context Fallback:</b> If Ollama is unavailable, offline, or still times out, the answer generator catches "
        "the exception and invokes a fallback handler (<a href='file:///c:/Users/srisa/OneDrive/Desktop/law-rag/legal-rag-assistant/generators/answer_generator.py#L48-L62'>generators/answer_generator.py</a>):<br/>"
        "• It parses the top reranked retrieved text passages directly.<br/>"
        "• It builds a clean, structured text output showing the relevant statutory clauses.<br/>"
        "• This guarantees that the user always receives the source information even during LLM offline events, achieving 100% availability.",
        style_body
    ))

    # ══════════════════════════════════════════════
    # SECTION 10: FRONTEND PORTAL
    # ══════════════════════════════════════════════
    story.append(Paragraph("10. Premium Frontend UI Portal Details", style_h1))
    story.append(Paragraph(
        "The user portal (<a href='file:///c:/Users/srisa/OneDrive/Desktop/law-rag/legal-rag-assistant/frontend_modern/index.html'>frontend_modern/index.html</a>) "
        "is built using Vanilla HTML/CSS/JavaScript. Rationale: Avoid heavy frontend framework builds to maintain zero build overhead, "
        "fast local load times, and simple integration.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Design Highlights:</b><br/>"
        "• <b>Color Palettes:</b> Sleek gold and ivory/cream tones with a deep slate background, conveying professional legal authority.<br/>"
        "• <b>Source Viewer Panel:</b> Allows side-by-side view. When a citation card is clicked in the main view, the source panel "
        "slides open, rendering the exact source section with highlighting.<br/>"
        "• <b>Legal Glossary:</b> A custom JavaScript tooltip scanner scans the response text. Over 35 legal Latin terms (e.g. <i>suo motu</i>, "
        "<i>prima facie</i>, <i>bona fide</i>) are marked, and hovering over them displays their legal definitions dynamically.",
        style_body
    ))
    story.append(Spacer(1, 10))
    story.append(PageBreak())

    # ══════════════════════════════════════════════
    # SECTION 11: INTERVIEW CHEAT SHEET
    # ══════════════════════════════════════════════
    story.append(Paragraph("11. Interview Preparation Cheat Sheet", style_h1))
    story.append(Paragraph(
        "Use this section to prepare for engineering interviews, reviewing RAG concepts and architectural decisions.",
        style_body
    ))
    
    # Q&As
    qas = [
        ("Q: What is the difference between a Bi-Encoder and a Cross-Encoder? Which is faster?",
         "A: A <b>Bi-Encoder</b> (e.g., SentenceTransformers) encodes query and document vectors independently, allowing vectors to be pre-computed and stored in databases like Chroma for fast similarity search. It is extremely fast. A <b>Cross-Encoder</b> takes the query and document together, passing them through self-attention layers to model token-level interactions. It is far more accurate but computationally expensive. We combine them: Bi-encoders retrieve a candidate set (top 15) and Cross-encoders rerank them (top 5)."),
         
        ("Q: How did you implement offline safety in this RAG architecture?",
         "A: We set the environment variable <font face='Courier'>HF_HUB_OFFLINE=\"1\"</font> to force PyTorch/Hugging Face to load models from the local disk cache (<font face='Courier'>~/.cache/huggingface</font>). Additionally, we used a local installation of Ollama serving <font face='Courier'>llama3</font> at <font face='Courier'>localhost:11434</font>. No data leaves the local network, preventing telemetry leaks and external API call dependency."),
         
        ("Q: Why not use a standard character-count text splitter for chunking?",
         "A: Legal clauses rely on structural coherence. If a section is split arbitrarily, the LLM loses context (such as exceptions, terms, or penalties defined at the end of the section). We created a section-aware parser that locates statutory dividers (like 'Section 43A:') and splits documents exactly along legal section lines."),
         
        ("Q: What happens if Ollama times out or crashes? How is your RAG resilient?",
         "A: We wrote a custom exception-catch mechanism in <font face='Courier'>generators/answer_generator.py</font>. If the client receives an HTTP Timeout, Connection Refused, or LLM failure, it bypasses LLM generation and enters an 'offline fallback' mode. It extracts the raw text from the top reranked chunks, formats it with metadata labels, and sends it directly to the UI, ensuring the assistant is still functional as a retrieval portal."),
         
        ("Q: How did you optimize Ollama client latency?",
         "A: Ollama loads weights on-demand, which causes first-run latency (up to 70-80s on CPU/GPU split). We solved this by (a) setting a connection pool timeout of 180 seconds, and (b) calling a warmup prompt at server startup to trigger LLM weights loading before the user sends their first query."),
         
        ("Q: How does the hybrid retrieval score fusion work?",
         "A: We retrieve documents from BM25 and Semantic search, normalize their scores to 0-1, and apply a weighted sum: <font face='Courier'>Score = alpha * SemanticScore + (1 - alpha) * BM25Score</font>. We set <font face='Courier'>alpha=0.7</font> to prioritize conceptual context while retaining keyword accuracy for statutory searches.")
    ]
    
    for q, a in qas:
        story.append(Paragraph(q, style_qa_q))
        story.append(Paragraph(a, style_qa_a))
        story.append(Spacer(1, 4))
        
    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)

if __name__ == "__main__":
    output_pdf = os.path.abspath(os.path.join("..", "law_read.pdf"))
    create_pdf(output_pdf)
    print(f"PDF successfully generated at: {output_pdf}")
