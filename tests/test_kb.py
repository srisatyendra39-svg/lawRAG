from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def mock_kb_registry(tmp_path, monkeypatch):
    test_registry_path = tmp_path / "knowledge_bases_test.json"
    monkeypatch.setattr("backend.routers.kb.REGISTRY_PATH", test_registry_path)
    return test_registry_path


def test_create_and_list_kbs(client) -> None:
    # 1. List KBs initially, should only have 'global'
    response = client.get(
        "/api/v1/kb/list",
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    kbs = response.json()
    assert len(kbs) == 1
    assert kbs[0]["kb_id"] == "global"

    # 2. Create a new custom KB
    payload = {"kb_id": "tax_law", "kb_name": "Tax Law Code"}
    response = client.post(
        "/api/v1/kb/create",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["kb_id"] == "tax_law"

    # 3. List KBs again, should have 'global' and 'tax_law'
    response = client.get(
        "/api/v1/kb/list",
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    kbs = response.json()
    assert len(kbs) == 2
    kb_ids = [k["kb_id"] for k in kbs]
    assert "global" in kb_ids
    assert "tax_law" in kb_ids


def test_create_kb_validation_errors(client) -> None:
    # 1. Invalid ID with spaces / special characters
    payload = {"kb_id": "Tax Law!", "kb_name": "Tax Law Code"}
    response = client.post(
        "/api/v1/kb/create",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 400
    assert "lowercase alphanumeric" in response.json()["detail"]

    # 2. Reserved ID 'global'
    payload = {"kb_id": "global", "kb_name": "Global DB"}
    response = client.post(
        "/api/v1/kb/create",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 400
    assert "reserved" in response.json()["detail"]

    # 3. Empty ID or name
    payload = {"kb_id": "", "kb_name": "Tax Law"}
    response = client.post(
        "/api/v1/kb/create",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 400


def test_create_duplicate_kb(client) -> None:
    payload = {"kb_id": "corporate_law", "kb_name": "Corporate Law"}
    
    # First creation
    response = client.post(
        "/api/v1/kb/create",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200

    # Duplicate creation
    response = client.post(
        "/api/v1/kb/create",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_delete_kb(client) -> None:
    # Create KB to delete
    payload = {"kb_id": "delete_me", "kb_name": "Delete Me"}
    response = client.post(
        "/api/v1/kb/create",
        json=payload,
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200

    # Delete KB
    response = client.post(
        "/api/v1/kb/delete",
        params={"kb_id": "delete_me"},
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Try listing, it should be gone
    response = client.get(
        "/api/v1/kb/list",
        headers={"X-API-Key": "test-secret-key"},
    )
    kbs = response.json()
    kb_ids = [k["kb_id"] for k in kbs]
    assert "delete_me" not in kb_ids


def test_delete_errors(client) -> None:
    # 1. Non-existent KB
    response = client.post(
        "/api/v1/kb/delete",
        params={"kb_id": "not_exists"},
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 404

    # 2. Cannot delete 'global'
    response = client.post(
        "/api/v1/kb/delete",
        params={"kb_id": "global"},
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code == 400
