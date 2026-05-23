# Legal RAG Assistant

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green)](https://fastapi.tiangolo.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-free-orange)](https://www.trychroma.com)

## Production-grade Legal Research Assistant using RAG

This repository implements a free, local Legal RAG system for Indian law: IT Act 2000, Constitution of India, and DPDP Act 2023.

## Architecture

```
PDFs -> PyMuPDF -> LegalChunker -> ChromaDB -> Hybrid Retrieval -> Reranker -> Ollama -> Legal Answer
```

## Features

- Free local stack: Ollama llama3, sentence-transformers, cross-encoder, ChromaDB, BM25
- Section-aware legal chunking
- Hybrid retrieval combining BM25 and semantic search
- Cross-encoder reranking for higher precision
- FastAPI API backend
- Premium Web Portal (Vanilla HTML/CSS/JS)
- RAGAS evaluation pipeline
- Docker-ready configuration

## Tech Stack

| Layer | Tool |
|---|---|
| Embeddings | sentence-transformers |
| Vector DB | ChromaDB |
| Semantic Search | LangChain + Chroma |
| Keyword Search | rank-bm25 |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| LLM | Ollama llama3 |
| API | FastAPI |
| Frontend | Premium HTML/CSS/JS Portal |

## Installation

```bash
cd legal-rag-assistant
pip install -r requirements.txt
cp .env.example .env
```

### Ollama Setup

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3
```

## Running Locally

```bash
python scripts/ingest_docs.py
uvicorn backend.main:app --reload
```

Open the premium web portal at `http://localhost:8000/portal/`.

## Docker Quickstart

```bash
docker-compose -f docker/docker-compose.yml up --build
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/ingest/document` | POST | Ingest a single PDF document |
| `/api/v1/ingest/all` | POST | Ingest all PDFs in `data/raw` |
| `/api/v1/ingest/status` | GET | Get ingestion status |
| `/api/v1/search/query` | POST | Run the full RAG QA pipeline |
| `/api/v1/search/retrieve` | POST | Run retrieval-only search |
| `/api/v1/search/filter` | GET | Filter chunks by act/chapter/section |
| `/api/v1/search/stream` | POST | Stream a generated answer |
| `/api/v1/evaluate/run` | POST | Run RAGAS evaluation |
| `/api/v1/evaluate/results` | GET | Fetch last evaluation results |
| `/health` | GET | Health and model status |

### Example curl

```bash
curl -X POST http://localhost:8000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What does Article 21 say?","top_k":5,"rewrite_query":true}'
```

## Why This Design?

- **Hybrid retrieval** combines exact section matching with semantic relevance.
- **Cross-encoder reranking** improves precision by scoring query-document pairs directly.
- **Section-aware chunking** preserves legal boundaries and avoids splitting clauses across chunks.
- **Ollama** removes API key dependency and keeps the stack free.

## Sample Queries

- "What are the penalties under Section 43 of IT Act?"
- "What does Article 21 say about right to life?"
- "How does DPDP Act define personal data?"
- "Compare privacy protections in Constitution and DPDP Act."

## Project Structure

```
legal-rag-assistant/
├── backend/
├── frontend_modern/
├── ingestion/
├── chunking/
├── embeddings/
├── vectorstore/
├── retrievers/
├── rerankers/
├── generators/
├── evaluation/
├── prompts/
├── models/
├── utils/
├── configs/
├── tests/
├── docker/
├── scripts/
├── data/
├── .env.example
├── requirements.txt
├── README.md
```
