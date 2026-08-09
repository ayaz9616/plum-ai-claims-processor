from collections.abc import Mapping
from typing import Any, Dict


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    return {}


def _infer_document_type(document: Dict[str, Any]) -> str:
    file_name = str(document.get("file_name") or "").lower()
    mime_type = str(document.get("mime_type") or "").lower()
    if "prescription" in file_name or "prescription" in mime_type:
        return "PRESCRIPTION"
    if "bill" in file_name or "invoice" in file_name or "bill" in mime_type:
        return "HOSPITAL_BILL"
    if "lab" in file_name or "report" in file_name:
        return "LAB_REPORT"
    if "pharmacy" in file_name or "drug" in file_name:
        return "PHARMACY_BILL"
    if "dental" in file_name:
        return "DENTAL_REPORT"
    return "UNKNOWN"


def is_fixture_document(document: Any) -> bool:
    """Fixture fields are an evaluation-only boundary, never inferred from uploads."""
    doc = _as_dict(document)
    return any(doc.get(key) is not None for key in ("actual_type", "content", "patient_name_on_doc", "quality"))


def normalize_fixture_document(document: Any) -> Dict[str, Any]:
    doc = _as_dict(document)
    content = _as_dict(doc.get("content") or doc.get("extracted"))
    document_type = str(doc.get("actual_type") or doc.get("document_type") or _infer_document_type(doc)).upper()
    quality = str(doc.get("quality") or content.get("quality") or "UNKNOWN").upper()
    patient_name = doc.get("patient_name_on_doc") or doc.get("name_on_doc") or content.get("patient_name")
    extracted = dict(content)
    if patient_name and "patient_name" not in extracted:
        extracted["patient_name"] = patient_name

    return {
        "file_id": str(doc.get("file_id") or doc.get("id") or "unknown"),
        "document_type": document_type,
        "quality": quality,
        "extracted": extracted,
        "source": {
            "file_name": doc.get("file_name"),
            "mime_type": doc.get("mime_type"),
            "size_bytes": doc.get("size_bytes"),
        },
    }


def normalize_uploaded_document(document: Any) -> Dict[str, Any]:
    """Keep an uploaded reference opaque until the backend extracts it."""
    doc = _as_dict(document)
    return {
        "file_id": str(doc.get("file_id") or doc.get("id") or "unknown"),
        "document_type": "UNKNOWN",
        "quality": "UNKNOWN",
        "extracted": {},
        "source": {"file_name": doc.get("file_name"), "mime_type": doc.get("mime_type"), "size_bytes": doc.get("size_bytes"), "fixture": False},
    }


def normalize_claim_input(claim: Any) -> Dict[str, Any]:
    raw = _as_dict(claim)
    documents = raw.get("documents") or []
    raw["documents"] = [
        normalize_fixture_document(document) if is_fixture_document(document) else normalize_uploaded_document(document)
        for document in documents
    ]
    return raw
