from __future__ import annotations

from pathlib import Path
import pytest


def test_health_endpoint(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_query_endpoint_valid_request(client) -> None:
    payload = {
        "question": "What is Section 43A of the IT Act?",
        "top_k": 3,
        "act_filter": None,
        "rewrite_query": False,
        "stream": False,
    }
    response = client.post(
        "/api/v1/search/query",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert len(data["citations"]) > 0
    assert data["citations"][0]["act_name"] == "Information Technology Act, 2000"


def test_query_endpoint_missing_question(client) -> None:
    payload = {
        "question": "",
        "top_k": 3,
        "act_filter": None,
        "rewrite_query": False,
        "stream": False,
    }
    response = client.post(
        "/api/v1/search/query",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 400


def test_retrieve_with_act_filter(client) -> None:
    payload = {
        "query": "Section 43A",
        "top_k": 2,
        "act_filter": "Information Technology Act, 2000",
        "chapter_filter": None,
        "use_reranker": True,
        "hybrid": True,
    }
    response = client.post(
        "/api/v1/search/retrieve",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["retrieval_method"] == "hybrid"
    assert len(data["results"]) > 0


def test_ingest_endpoint(client) -> None:
    import fitz
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = raw_dir / "sample_test_doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Section 43A: Compensation for failure to protect data.")
    doc.save(pdf_path)
    doc.close()
    
    payload = {
        "file_path": str(pdf_path),
        "act_name": "Information Technology Act, 2000",
        "overwrite": True,
    }
    try:
        response = client.post(
            "/api/v1/ingest/document",
            json=payload,
            headers={"X-API-Key": "test-secret-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    finally:
        if pdf_path.exists():
            pdf_path.unlink()


def test_correlation_id_and_latency_headers(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert "X-Response-Time-Ms" in response.headers
    # Test that setting X-Correlation-ID in request returns the same in response
    test_id = "test-corr-id-12345"
    response = client.get("/health", headers={"X-Correlation-ID": test_id})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == test_id


def test_structured_error_validation(client) -> None:
    # Send non-integer top_k to trigger request validation error
    payload = {
        "question": "What is Section 43A?",
        "top_k": "invalid-int",
    }
    response = client.post(
        "/api/v1/search/query",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "detail" in data


def test_structured_error_unauthorized(client) -> None:
    payload = {
        "question": "What is Section 43A of the IT Act?",
    }
    response = client.post(
        "/api/v1/search/query",
        json=payload,
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "HTTP_401"
    assert data["detail"] == "Invalid or missing API Key"


def test_query_endpoint_parameter_overrides(client) -> None:
    payload = {
        "question": "What is Section 43A?",
        "top_k": 2,
        "temperature": 0.0,
        "hybrid_alpha": 0.7,
    }
    response = client.post(
        "/api/v1/search/query",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data

