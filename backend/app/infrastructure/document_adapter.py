from typing import Any, Dict, Optional
import json
import re
from pathlib import Path
from backend.app.schemas import NormalizedDocument, StructuredDocumentData
from backend.app.infrastructure.providers import ProviderSet, VisionRequest
from backend.app.extraction_normalize import DocumentExtractionNormalizationError, parse_structured_document
from backend.uploads import STAGING_DIR

class ProductionDocumentAdapter:
    """Backend-owned adapter from staged upload to validated extraction data."""
    def __init__(self, providers: Optional[ProviderSet]):
        self.vision = providers.vision if providers else None

    @staticmethod
    def _mime_type(document: Dict[str, Any]) -> str:
        supplied = document.get("source", {}).get("mime_type")
        if supplied:
            return str(supplied)
        suffix = Path(str(document.get("file_id", ""))).suffix.lower()
        return {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffix, "application/octet-stream")

    @staticmethod
    def _parse_response(text: str, structured: Optional[Dict[str, Any]] = None) -> StructuredDocumentData:
        if isinstance(structured, dict) and structured:
            payload = dict(structured)
        else:
            cleaned = (text or "").strip()
            if not cleaned:
                raise ValueError("document extraction returned an empty response")
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
            try:
                payload = json.loads(cleaned)
            except json.JSONDecodeError:
                start, end = cleaned.find("{"), cleaned.rfind("}")
                if start < 0 or end <= start:
                    raise ValueError("document extraction did not return valid JSON")
                try:
                    payload = json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError as exc:
                    raise ValueError("document extraction returned malformed JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("document extraction returned an unexpected response format")
        # Gemini sometimes uses `date`; converge that provider detail at the boundary.
        if "treatment_date" not in payload and payload.get("date"):
            payload["treatment_date"] = payload["date"]
        payload["document_type"] = re.sub(r"[\s-]+", "_", str(payload.get("document_type") or "UNKNOWN").upper())
        quality = str(payload.get("quality") or "UNKNOWN").upper()
        payload["quality"] = {"HIGH": "GOOD", "READABLE": "GOOD", "MEDIUM": "LOW", "POOR": "LOW", "UNREADABLE": "UNREADABLE"}.get(quality, quality)
        try:
            parsed, _financial_mismatches = parse_structured_document(payload)
        except DocumentExtractionNormalizationError as exc:
            raise ValueError(f"document extraction normalization failed: {exc}") from exc
        return parsed

    def materialize(self, document: Dict[str, Any]) -> NormalizedDocument:
        # Fixture extraction is explicit and exists solely to exercise the same workflow contract.
        if document.get("source", {}).get("fixture") is not False:
            return NormalizedDocument(**document)
        if not self.vision:
            raise RuntimeError("Gemini Vision API is not configured for uploaded-document processing")
        document_id = str(document.get("file_id") or "")
        if not document_id or ".." in document_id:
            raise RuntimeError("invalid staged document reference")
        staged_path = STAGING_DIR / document_id
        if not staged_path.exists():
            raise RuntimeError("uploaded document was not found in staging")
        prompt = """Extract this medical claim document. Return ONLY JSON with: document_type (PRESCRIPTION, HOSPITAL_BILL, PHARMACY_BILL, LAB_REPORT, DIAGNOSTIC_REPORT, DENTAL_REPORT, UNKNOWN), patient_name, treatment_date (YYYY-MM-DD when possible), hospital_name, diagnosis, treatment, line_items ([{description, amount}]), subtotal, tax, discount, other_charges, grand_total, amount_payable, amount_received, total, quality (GOOD, LOW, UNREADABLE), confidence (0..1). Preserve each labelled monetary value; use null/[] where unknown and do not infer arithmetic or policy decisions."""
        response = self.vision.analyze(VisionRequest(document_path=str(staged_path), mime_type=self._mime_type(document), metadata={"prompt": prompt}))
        parsed = self._parse_response(response.text, response.structured)
        # A successfully consumed document no longer needs to remain staged.
        staged_path.unlink(missing_ok=True)
        extracted = parsed.model_dump(mode="python", exclude={"document_type", "quality", "confidence"}, exclude_none=True)
        return NormalizedDocument(file_id=document_id, document_type=parsed.document_type.upper(), quality=parsed.quality.upper(), extracted=extracted, source={**document.get("source", {}), "fixture": False, "provider": response.metadata.get("model")})