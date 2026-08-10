from typing import Dict, Any, List
import json
from decimal import Decimal
from backend.app.schemas import DocumentClassification, DocumentVerificationResult, DocumentArtifact, DocumentQualityResult, NormalizedDocument
from backend.app.infrastructure.providers import ProviderSet
from backend.app.errors import DocumentMismatchError, DocumentUnreadableError


class DocumentClassifier:
    def classify(self, documents: List[NormalizedDocument]) -> List[DocumentClassification]:
        classifications: List[DocumentClassification] = []
        for document in documents:
            signals = [f"source:{document.source.get('file_name') or document.file_id}"]
            if document.quality == "UNREADABLE":
                signals.append("quality:unreadable")
            classifications.append(
                DocumentClassification(
                    file_id=document.file_id,
                    document_type=document.document_type,
                    confidence=Decimal("0.99") if document.document_type != "UNKNOWN" else Decimal("0.50"),
                    quality=document.quality,
                    signals=signals,
                )
            )
        return classifications


class DocumentVerifier:
    def verify(
        self,
        claim: Dict[str, Any],
        classifications: List[DocumentClassification],
        policy_raw: Dict[str, Any],
        *,
        types_only: bool = False,
    ) -> DocumentVerificationResult:
        category = str(claim.get("claim_category") or "")
        requirement_block = policy_raw.get("document_requirements", {}).get(category.upper(), {})
        required = list(requirement_block.get("required", []))
        if types_only:
            provided = [classification.document_type for classification in classifications]
            unreadable: List[str] = []
        else:
            provided = [classification.document_type for classification in classifications if classification.quality != "UNREADABLE"]
            unreadable = [classification.file_id for classification in classifications if classification.quality == "UNREADABLE"]
        missing = [required_type for required_type in required if required_type not in provided]
        wrong_type = []
        if missing:
            wrong_type = [classification.document_type for classification in classifications if classification.document_type not in required]
        ok = not missing and (types_only or not unreadable)
        message = "documents verified"
        if not types_only and unreadable:
            unreadable_types = [c.document_type.replace("_", " ").lower() for c in classifications if c.file_id in unreadable]
            message = f"please re-upload a clear {' and '.join(unreadable_types)}"
        elif missing:
            uploaded = ", ".join(provided) or "no usable documents"
            message = f"you uploaded {uploaded}, but {' and '.join(missing)} is required for this {category.lower()} claim"
        return DocumentVerificationResult(
            ok=ok,
            status="BLOCKED_DOCUMENT" if not ok else "VERIFIED",
            message=message,
            required=required,
            provided=provided,
            missing=missing,
            unreadable=unreadable,
            wrong_type=wrong_type,
        )


class DocumentQualityGate:
    """Use structured extraction evidence to prevent type recognition becoming a readability pass."""
    _BILL_TYPES = {"PHARMACY_BILL"}

    @staticmethod
    def _present(value: Any) -> bool:
        return value is not None and str(value).strip().lower() not in {"", "none", "null", "unknown", "n/a"}

    @classmethod
    def assess(cls, documents: List[NormalizedDocument]) -> List[DocumentQualityResult]:
        results: List[DocumentQualityResult] = []
        for document in documents:
            document_type = document.document_type.upper()
            original_quality = document.quality.upper()
            fields: List[str] = []
            payload = document.extracted
            if document_type in cls._BILL_TYPES:
                if not cls._present(payload.get("patient_name")):
                    fields.append("patient_name")
                if not cls._present(payload.get("treatment_date") or payload.get("date")):
                    fields.append("bill_date")
                if not cls._present(payload.get("hospital_name") or payload.get("pharmacy_name") or payload.get("provider_name")):
                    fields.append("pharmacy_provider_name")
                line_items = payload.get("line_items") or []
                reliable_line_items = bool(line_items) and all(
                    isinstance(item, dict) and cls._present(item.get("amount"))
                    for item in line_items
                )
                reliable_total = any(cls._present(payload.get(key)) for key in ("total", "grand_total", "amount_payable"))
                if not reliable_line_items:
                    fields.append("line_item_amounts")
                if not reliable_total:
                    fields.append("total_amount")

                # A billing document cannot be adjudicated without both identity/date/provider
                # evidence and a reliable way to establish the payable amount.
                quality = "GOOD" if not fields else "UNREADABLE"
                reason = "Critical billing fields could not be reliably read" if fields else "Critical billing fields were reliably extracted"
            else:
                quality = original_quality
                reason = "No bill-specific readability gate applies"
            if original_quality == "UNREADABLE":
                quality = "UNREADABLE"
                reason = "Document was reported as unreadable"
            results.append(DocumentQualityResult(
                file_id=document.file_id, document_type=document_type, quality=quality,
                reason=reason, missing_or_unreliable_fields=fields,
            ))
        return results


