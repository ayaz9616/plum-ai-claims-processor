import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from backend.main import app, provider_set
from backend.app.infrastructure.providers import VisionResponse
from backend.uploads import STAGING_DIR

client = TestClient(app)

@pytest.fixture
def mock_vision():
    original = provider_set.vision
    mock = MagicMock()
    provider_set.vision = mock
    yield mock
    provider_set.vision = original

def test_ocr_missing_document(mock_vision):
    response = client.post("/api/documents/non_existent_doc.pdf/ocr")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    mock_vision.analyze.assert_not_called()

def test_ocr_success(mock_vision):
    # Setup staged file
    doc_id = "test_doc_ocr_success.pdf"
    staged_path = STAGING_DIR / doc_id
    staged_path.write_bytes(b"%PDF-1.4...")
    
    mock_vision.analyze.return_value = VisionResponse(
        text="Mocked document text",
        structured={},
        metadata={"model": "mock-model"}
    )
    
    try:
        response = client.post(f"/api/documents/{doc_id}/ocr")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["text"] == "Mocked document text"
        assert body["document_id"] == doc_id
    finally:
        staged_path.unlink(missing_ok=True)
    
    # Assert file is cleaned up
    assert not staged_path.exists()

def test_ocr_gemini_failure(mock_vision):
    doc_id = "test_doc_ocr_fail.pdf"
    staged_path = STAGING_DIR / doc_id
    staged_path.write_bytes(b"%PDF-1.4...")
    
    mock_vision.analyze.side_effect = RuntimeError("API down")
    
    try:
        response = client.post(f"/api/documents/{doc_id}/ocr")
        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()
    finally:
        staged_path.unlink(missing_ok=True)
    
    # Assert file is cleaned up even on failure
    assert not staged_path.exists()

def test_ocr_provider_not_configured():
    original = provider_set.vision
    provider_set.vision = None
    try:
        response = client.post("/api/documents/some_doc.pdf/ocr")
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()
    finally:
        provider_set.vision = original
