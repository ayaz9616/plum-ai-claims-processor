from io import BytesIO

from fastapi.testclient import TestClient

from backend.main import app
from backend.temp_documents import temporary_document_path


client = TestClient(app)


def test_document_upload_accepts_pdf():
    pdf_bytes = b"%PDF-1.4\n% upload test\n"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.pdf", BytesIO(pdf_bytes), "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["filename"] == "sample.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(pdf_bytes)


def test_document_upload_rejects_unsupported_type():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_temporary_document_cleanup():
    with temporary_document_path(b"cleanup-test", suffix=".png") as temp_path:
        assert temp_path.exists()

    assert not temp_path.exists()


def test_document_upload_missing_file():
    response = client.post("/api/documents/upload")
    assert response.status_code == 422


from unittest.mock import patch

def test_document_upload_rejects_oversized_file():
    with patch("backend.uploads.MAX_UPLOAD_BYTES", 10):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("large.pdf", BytesIO(b"0123456789A"), "application/pdf")},
        )
        assert response.status_code == 413
        assert "size limit" in response.json()["detail"].lower()