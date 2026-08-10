from decimal import Decimal
from datetime import datetime
from backend.app.core.identity import normalize_identity_name
from typing import Dict, Any, List
import json
from backend.app.schemas import ConsistencyResult, MemberDocumentConsistencyResult, DocumentExtraction, MemberResolutionResult
from backend.app.infrastructure.providers import ProviderSet


class ConsistencyAgent:
    @staticmethod
    def bill_arithmetic_verifiable(extractions: List[DocumentExtraction]) -> bool:
        bills = [e for e in extractions if e.document_type.upper() in {"PHARMACY_BILL", "HOSPITAL_BILL"}]
        if not bills:
            return True
        for extraction in bills:
            payload = extraction.extracted
            items = payload.get("line_items") or []
            total = payload.get("amount_payable", payload.get("grand_total", payload.get("total")))
            if not items or total is None or any(not isinstance(item, dict) or item.get("amount") is None for item in items):
                return False
        return True

    def check(self, extractions: List[DocumentExtraction]) -> ConsistencyResult:
        names = []
        for extraction in extractions:
            patient_name = extraction.extracted.get("patient_name")
            if patient_name:
                names.append(normalize_identity_name(str(patient_name)))
        unique_names = sorted(set(names))
        mismatches: List[Dict[str, Any]] = []
        if len(unique_names) > 1:
            mismatches.append({"field": "patient_name", "found_names": unique_names, "severity": "CRITICAL", "action": "BLOCK", "reason": "documents contain different patient identities"})
        def normalized_date(value: Any) -> str:
            raw = str(value).strip()
            for date_format in ("%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(raw, date_format).date().isoformat()
                except ValueError:
                    continue
            return raw
        dates = sorted({normalized_date(e.extracted.get("treatment_date") or e.extracted.get("date")) for e in extractions if e.extracted.get("treatment_date") or e.extracted.get("date")})
        if len(dates) > 1:
            mismatches.append({"field": "treatment_date", "found_dates": dates, "severity": "CRITICAL", "action": "BLOCK", "reason": "documents contain different treatment dates"})
        for extraction in extractions:
            payload = extraction.extracted
            items = payload.get("line_items") or []
            stated_amount = payload.get("amount_payable", payload.get("grand_total", payload.get("total")))
            if items and stated_amount is not None:
                try:
                    line_sum = sum((Decimal(str(item.get("amount", 0))) for item in items), Decimal("0"))
                    total = Decimal(str(stated_amount))
                    if line_sum != total:
                        mismatches.append({"field": "bill_total", "file_id": extraction.file_id, "line_item_total": str(line_sum), "amount_payable": str(payload.get("amount_payable")) if payload.get("amount_payable") is not None else None, "grand_total": str(payload.get("grand_total")) if payload.get("grand_total") is not None else None, "document_total": str(payload.get("total")) if payload.get("total") is not None else None, "severity": "REVIEW", "action": "MANUAL_REVIEW", "reason": "bill contains conflicting financial totals"})
                except Exception:
                    mismatches.append({"field": "bill_total", "file_id": extraction.file_id, "severity": "REVIEW", "action": "MANUAL_REVIEW", "reason": "bill arithmetic fields could not be compared"})
        critical = [m for m in mismatches if m.get("severity") == "CRITICAL"]
        ok = not critical
        message = "documents consistent"
        if mismatches:
            message = "; ".join(m.get("reason", f"{m.get('field', 'document')} mismatch") for m in mismatches)
        return ConsistencyResult(ok=ok, message=message, found_names=unique_names, mismatches=mismatches, review_required=bool(mismatches and not critical))


class MemberDocumentConsistencyAgent:
    def check(self, member_res: MemberResolutionResult, extractions: List[DocumentExtraction]) -> MemberDocumentConsistencyResult:
        if not member_res.member_found:
            return MemberDocumentConsistencyResult(consistent=False, mismatches=[{"reason": "member not found"}])
        allowed = {normalize_identity_name(member_res.member_name)} | {normalize_identity_name(d.get("name", "")) for d in member_res.dependents}
        mismatches = []
        for ext in extractions:
            doc_name = str(ext.extracted.get("patient_name") or "")
            if doc_name:
                norm_doc_name = normalize_identity_name(doc_name)
                if norm_doc_name not in allowed:
                    mismatches.append({
                        "field": "patient_name",
                        "document": doc_name,
                        "resolved_member": member_res.member_name,
                        "document_patient": doc_name,
                        "reason": "Identity mismatch between policy member and document patient"
                    })
        return MemberDocumentConsistencyResult(consistent=len(mismatches) == 0, mismatches=mismatches)


