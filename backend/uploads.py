from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from .app.errors import PlumError
from .temp_documents import TempDocumentHandle, temporary_document_path

SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_UPLOAD_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class DocumentUploadError(PlumError):
    code = "DOCUMENT_UPLOAD_ERROR"


@dataclass
class DocumentUploadResult:
    status: str
    message: str
    filename: str
    content_type: str
    size_bytes: int
    document_id: str = ""
    accepted: bool = True


def _normalize_suffix(filename: Optional[str]) -> str:
    if not filename:
        return ".bin"
    suffix = Path(filename).suffix.lower()
    return suffix if suffix else ".bin"


def validate_upload_metadata(filename: str, content_type: Optional[str]) -> None:
    suffix = _normalize_suffix(filename)
    if suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise DocumentUploadError(
            "Unsupported file type. Please upload a PDF, PNG, JPG, JPEG, or WEBP image."
        )
    if content_type and content_type.lower() not in SUPPORTED_UPLOAD_MIME_TYPES:
        raise DocumentUploadError(
            "Unsupported content type. Please upload a PDF, PNG, JPG, JPEG, or WEBP image."
        )

import uuid
import tempfile
import os

STAGING_DIR = Path(tempfile.gettempdir()) / "plum_claims_staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

class DocumentUploadService:
    def process_upload(self, upload_file: UploadFile) -> DocumentUploadResult:
        filename = upload_file.filename or "uploaded_document"
        content_type = upload_file.content_type or "application/octet-stream"
        validate_upload_metadata(filename, content_type)

        suffix = _normalize_suffix(filename)
        document_id = f"{uuid.uuid4()}{suffix}"
        staged_path = STAGING_DIR / document_id
        
        size_bytes = 0
        try:
            with open(staged_path, "wb") as temp_handle:
                while True:
                    chunk = upload_file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > MAX_UPLOAD_BYTES:
                        raise DocumentUploadError(
                            f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB size limit."
                        )
                    temp_handle.write(chunk)

            return DocumentUploadResult(
                status="uploaded",
                message="Document validated and staged temporarily.",
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
                document_id=document_id,
                accepted=True,
            )
        except Exception:
            try:
                staged_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise
        finally:
            try:
                upload_file.file.seek(0)
            except Exception:
                pass


