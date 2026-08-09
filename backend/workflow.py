from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
import re
import json
from pathlib import Path

from langgraph.graph import END, StateGraph

from .adapter import normalize_claim_input
from .providers import ProviderSet, VisionRequest
from .uploads import STAGING_DIR
from .policy import PolicyRepository
from .policy_evaluator import PolicyEvaluator
from .storage import ClaimAuditRepository
from .schemas import (
    ClaimProcessingResult,
    ConfidenceResult,
    ConsistencyResult,
    DecisionResult,
    DocumentClassification,
    DocumentExtraction,
    DocumentVerificationResult,
    FinancialCalculationResult,
    FraudAnalysis,
    MemberResolutionResult,
    MemberDocumentConsistencyResult,
    NormalizedDocument,
    StructuredDocumentData,
    PolicyEvaluation,
    TraceEvent,
)
from .trace import TraceManager


class ClaimState(TypedDict, total=False):
    claim_id: str
    raw_claim: Dict[str, Any]
    normalized_claim: Dict[str, Any]
    policy_raw: Dict[str, Any]
    policy_evaluation_result: PolicyEvaluation
    member_resolution_result: MemberResolutionResult
    member_document_consistency_result: MemberDocumentConsistencyResult
    document_classifications: List[DocumentClassification]
    document_verification_result: DocumentVerificationResult
    document_extractions_result: List[DocumentExtraction]
    prepared_documents: List[NormalizedDocument]
    consistency_result: ConsistencyResult
    financials_result: FinancialCalculationResult
    fraud_result: FraudAnalysis
    confidence_result: ConfidenceResult
    decision_result: DecisionResult
    result: ClaimProcessingResult
    degraded: bool
    component_failures: List[Dict[str, Any]]
    blocked_reason: str
    manual_review_reason: str
    policy_rejection_reason: str


def _trace_event(
    trace_manager: TraceManager,
    claim_id: str,
    step: str,
    component: str,
    status: str,
    safe_input: Optional[Any] = None,
    safe_output: Optional[Any] = None,
    evidence: Optional[Any] = None,
    error: Optional[str] = None,
    summary: Optional[str] = None,
    reason_code: Optional[str] = None,
) -> None:
    summaries = {
        "INPUT_VALIDATION": "Claim input was checked for the required claim details and document references.",
        "MEMBER_RESOLUTION": "Member and policy eligibility were resolved against the authoritative policy roster.",
        "DOCUMENT_CLASSIFICATION": "Uploaded documents were classified from their extracted evidence.",
        "DOCUMENT_EXTRACTION": "Structured claim fields were extracted from the uploaded documents.",
        "DOCUMENT_QUALITY": "Document readability was checked before adjudication.",
        "DOCUMENT_VERIFICATION": "Submitted document types were checked against the policy requirements.",
        "MEMBER_DOCUMENT_CONSISTENCY": "Extracted patient identities were compared with the resolved policy member.",
        "CROSS_DOCUMENT_CONSISTENCY": "Patient names, dates, and bill arithmetic were compared across documents.",
        "POLICY_EVALUATION": "Deterministic policy coverage, limits, exclusions, and pre-authorization rules were evaluated.",
        "FINANCIAL_CALCULATION": "Approved amount was calculated deterministically from policy terms.",
        "FRAUD_ANALYSIS": "Available claim-history fraud indicators were evaluated.",
        "CONFIDENCE": "Confidence was calculated from completed and degraded components.",
        "DECISION": "The final claim processing outcome was recorded.",
    }
    trace_manager.add_event(
        TraceEvent(
            trace_id=str(uuid.uuid4()),
            claim_id=claim_id,
            step=step,
            component=component,
            status=status,
            duration_ms=0,
            safe_input=safe_input,
            safe_output=safe_output,
            evidence=evidence,
            error=error,
            summary=summary or summaries.get(step),
            reason_code=reason_code,
        )
    )


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
    def _parse_response(text: str) -> StructuredDocumentData:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start < 0 or end <= start:
                raise
            payload = json.loads(cleaned[start:end + 1])
        # Gemini sometimes uses `date`; converge that provider detail at the boundary.
        if "treatment_date" not in payload and payload.get("date"):
            payload["treatment_date"] = payload["date"]
        payload["document_type"] = re.sub(r"[\s-]+", "_", str(payload.get("document_type") or "UNKNOWN").upper())
        quality = str(payload.get("quality") or "UNKNOWN").upper()
        payload["quality"] = {"HIGH": "GOOD", "READABLE": "GOOD", "MEDIUM": "LOW", "POOR": "LOW", "UNREADABLE": "UNREADABLE"}.get(quality, quality)
        return StructuredDocumentData.model_validate(payload)

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
        prompt = """Extract this medical claim document. Return ONLY JSON with: document_type (PRESCRIPTION, HOSPITAL_BILL, PHARMACY_BILL, LAB_REPORT, DIAGNOSTIC_REPORT, DENTAL_REPORT, UNKNOWN), patient_name, treatment_date (YYYY-MM-DD when possible), hospital_name, diagnosis, treatment, line_items ([{description, amount}]), total, quality (GOOD, LOW, UNREADABLE), confidence (0..1). Use null/[] where unknown; do not infer arithmetic or policy decisions."""
        response = self.vision.analyze(VisionRequest(document_path=str(staged_path), mime_type=self._mime_type(document), metadata={"prompt": prompt}))
        parsed = self._parse_response(response.text)
        # A successfully consumed document no longer needs to remain staged.
        staged_path.unlink(missing_ok=True)
        extracted = parsed.model_dump(mode="python", exclude={"document_type", "quality", "confidence"}, exclude_none=True)
        return NormalizedDocument(file_id=document_id, document_type=parsed.document_type.upper(), quality=parsed.quality.upper(), extracted=extracted, source={**document.get("source", {}), "fixture": False, "provider": response.metadata.get("model")})


class DocumentVerifier:
    def verify(self, claim: Dict[str, Any], classifications: List[DocumentClassification], policy_raw: Dict[str, Any]) -> DocumentVerificationResult:
        category = str(claim.get("claim_category") or "")
        requirement_block = policy_raw.get("document_requirements", {}).get(category.upper(), {})
        required = list(requirement_block.get("required", []))
        provided = [classification.document_type for classification in classifications if classification.quality != "UNREADABLE"]
        unreadable = [classification.file_id for classification in classifications if classification.quality == "UNREADABLE"]
        missing = [required_type for required_type in required if required_type not in provided]
        wrong_type = []
        if missing:
            wrong_type = [classification.document_type for classification in classifications if classification.document_type not in required]
        ok = not missing and not unreadable
        message = "documents verified"
        if unreadable:
            message = f"re-upload required for unreadable document(s): {', '.join(unreadable)}"
        elif missing:
            message = f"missing required document(s): {', '.join(missing)}"
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


class DocumentExtractor:
    def extract(self, documents: List[NormalizedDocument]) -> List[DocumentExtraction]:
        extracted: List[DocumentExtraction] = []
        for document in documents:
            extracted.append(
                DocumentExtraction(
                    file_id=document.file_id,
                    document_type=document.document_type,
                    extracted=document.extracted,
                    confidence=Decimal("0.95") if document.quality != "UNREADABLE" else Decimal("0.30"),
                )
            )
        return extracted


class ConsistencyAgent:
    def check(self, extractions: List[DocumentExtraction]) -> ConsistencyResult:
        names = []
        for extraction in extractions:
            patient_name = extraction.extracted.get("patient_name")
            if patient_name:
                names.append(str(patient_name).strip())
        unique_names = sorted(set(names))
        mismatches: List[Dict[str, Any]] = []
        if len(unique_names) > 1:
            mismatches.append({"field": "patient_name", "found_names": unique_names, "reason": "cross-document patient mismatch"})
        dates = sorted({str(e.extracted.get("treatment_date") or e.extracted.get("date")).strip() for e in extractions if e.extracted.get("treatment_date") or e.extracted.get("date")})
        if len(dates) > 1:
            mismatches.append({"field": "treatment_date", "found_dates": dates, "reason": "cross-document treatment date mismatch"})
        for extraction in extractions:
            payload = extraction.extracted
            items = payload.get("line_items") or []
            if items and payload.get("total") is not None:
                try:
                    line_sum = sum((Decimal(str(item.get("amount", 0))) for item in items), Decimal("0"))
                    total = Decimal(str(payload["total"]))
                    if line_sum != total:
                        mismatches.append({"field": "bill_total", "file_id": extraction.file_id, "line_item_sum": str(line_sum), "bill_total": str(total), "difference": str(line_sum-total), "consistency_status": "MISMATCH"})
                except Exception:
                    mismatches.append({"field": "bill_total", "file_id": extraction.file_id, "reason": "bill arithmetic fields are invalid", "consistency_status": "INVALID"})
        ok = not mismatches
        message = "documents consistent"
        if not ok:
            message = "; ".join(m.get("reason", f"{m.get('field', 'document')} mismatch") for m in mismatches)
        return ConsistencyResult(ok=ok, message=message, found_names=unique_names, mismatches=mismatches)

# New helper to normalize names
def _normalize_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'^(mr\.|ms\.|mrs\.|dr\.)\s*', '', name, flags=re.IGNORECASE)
    return name.strip().lower()

class MemberResolver:
    """Resolve member and policy validity using policy_terms.json data."""
    def resolve(self, claim: Dict[str, Any], policy_raw: Dict[str, Any]) -> MemberResolutionResult:
        member_id = claim.get("member_id")
        policy_id = claim.get("policy_id")
        treatment_date_str = claim.get("treatment_date")
        errors = []
        if not policy_raw or policy_raw.get("policy_id") != policy_id:
            errors.append(f"Policy not found or mismatch: {policy_id}")
            return MemberResolutionResult(
                member_id=str(member_id), member_name="", member_found=False,
                policy_id=str(policy_id), policy_valid=False, eligible=False, errors=errors)
        # Date validity
        try:
            td = datetime.fromisoformat(treatment_date_str).date()
            start = policy_raw.get("policy_holder", {}).get("policy_start_date") or policy_raw.get("policy_start_date")
            end = policy_raw.get("policy_holder", {}).get("policy_end_date") or policy_raw.get("policy_end_date")
            if start and end:
                sd = datetime.fromisoformat(start).date()
                ed = datetime.fromisoformat(end).date()
                if not (sd <= td <= ed):
                    errors.append("Treatment date outside policy period")
        except Exception:
            pass
        members = policy_raw.get("members", [])
        found_member = next((m for m in members if m.get("member_id") == member_id), None)
        if not found_member:
            errors.append(f"Member {member_id} not found in policy")
            return MemberResolutionResult(
                member_id=str(member_id), member_name="", member_found=False,
                policy_id=str(policy_id), policy_valid=True, eligible=False, errors=errors)
        primary_member = found_member
        if found_member.get("relationship") != "SELF":
            primary_id = found_member.get("primary_member_id")
            primary_member = next((m for m in members if m.get("member_id") == primary_id), None)
            if not primary_member or found_member.get("member_id") not in primary_member.get("dependents", []):
                errors.append("Invalid dependent relationship")
        try:
            if primary_member and primary_member.get("join_date") and treatment_date_str:
                jd = datetime.fromisoformat(primary_member.get("join_date")).date()
                td = datetime.fromisoformat(treatment_date_str).date()
                if jd > td:
                    errors.append("Treatment date before join date")
        except Exception:
            pass
        dependent_records = [
            {"dependent_id": dependent.get("member_id"), "name": dependent.get("name"), "relationship": dependent.get("relationship"), "primary_member_id": dependent.get("primary_member_id")}
            for dependent in members if dependent.get("primary_member_id") == found_member.get("member_id")
        ] if found_member.get("relationship") == "SELF" else []
        return MemberResolutionResult(
            member_id=str(member_id), member_name=found_member.get("name", ""), member_found=True,
            policy_id=str(policy_id), policy_valid=True, eligible=len(errors) == 0,
            dependents=dependent_records,
            errors=errors
        )

class MemberDocumentConsistencyAgent:
    def check(self, member_res: MemberResolutionResult, extractions: List[DocumentExtraction]) -> MemberDocumentConsistencyResult:
        if not member_res.member_found:
            return MemberDocumentConsistencyResult(consistent=False, mismatches=[{"reason": "member not found"}])
        allowed = {_normalize_name(member_res.member_name)} | {_normalize_name(d.get("name", "")) for d in member_res.dependents}
        mismatches = []
        for ext in extractions:
            doc_name = str(ext.extracted.get("patient_name") or "")
            if doc_name:
                norm_doc_name = _normalize_name(doc_name)
                if norm_doc_name not in allowed:
                    mismatches.append({
                        "field": "patient_name",
                        "document": doc_name,
                        "resolved_member": member_res.member_name,
                        "document_patient": doc_name,
                        "reason": "Identity mismatch between policy member and document patient"
                    })
        return MemberDocumentConsistencyResult(consistent=len(mismatches) == 0, mismatches=mismatches)


class CalculationEngine:
    def calculate(self, claim: Dict[str, Any], policy_raw: Dict[str, Any]) -> FinancialCalculationResult:
        category = str(claim.get("claim_category") or "").lower()
        category_policy = policy_raw.get("opd_categories", {}).get(category, {}) or {}
        claimed_amount = Decimal(str(claim.get("claimed_amount", 0)))

        if category.upper() == "DENTAL":
            approved_amount = Decimal("0")
            excluded = {str(item).lower() for item in category_policy.get("excluded_procedures", [])}
            covered = set()
            line_items = []
            for document in claim.get("documents", []):
                for item in (document.get("extracted", {}) or {}).get("line_items", []) or []:
                    description = str(item.get("description") or "")
                    amount = Decimal(str(item.get("amount", 0)))
                    is_excluded = any(exclusion in description.lower() for exclusion in excluded)
                    if is_excluded:
                        line_items.append({
                            "description": description,
                            "claimed_amount": str(amount),
                            "eligible": False,
                            "approved_amount": "0",
                            "reason": "Policy exclusion"
                        })
                        continue
                    approved_amount += amount
                    covered.add(description)
                    line_items.append({
                        "description": description,
                        "claimed_amount": str(amount),
                        "eligible": True,
                        "approved_amount": str(amount),
                        "reason": "Covered by policy"
                    })
            breakdown = {
                "covered_line_items": sorted(covered),
                "excluded_procedures": sorted(excluded),
                "line_items": line_items
            }
            decision_hint = "PARTIAL" if approved_amount > 0 else "REJECTED"
            return FinancialCalculationResult(approved_amount=approved_amount, decision_hint=decision_hint, breakdown=breakdown)

        hospital_name = str(claim.get("hospital_name") or "")
        network_hospitals = {str(hospital).lower() for hospital in policy_raw.get("network_hospitals", [])}
        is_network = hospital_name.lower() in network_hospitals if hospital_name else False
        amount = claimed_amount
        breakdown: Dict[str, Any] = {"claimed": str(claimed_amount), "network_applied": is_network}

        discount_pct = Decimal(str(category_policy.get("network_discount_percent", 0)))
        if is_network and discount_pct > 0:
            network_discount = (amount * discount_pct) / Decimal(100)
            amount -= network_discount
            breakdown["network_discount"] = str(network_discount)
        else:
            breakdown["network_discount"] = "0"

        copay_pct = Decimal(str(category_policy.get("copay_percent", 0)))
        copay = (amount * copay_pct) / Decimal(100)
        approved_amount = amount - copay
        breakdown["copay"] = str(copay)
        breakdown["approved"] = str(approved_amount)
        return FinancialCalculationResult(approved_amount=approved_amount, decision_hint="APPROVED", breakdown=breakdown)


class FraudAnalyzer:
    def analyze(self, claim: Dict[str, Any], policy_raw: Dict[str, Any]) -> FraudAnalysis:
        if claim.get("simulate_component_failure"):
            return FraudAnalysis(ok=True, manual_review=False, signals=[{"type": "component_failure", "component": "FraudAnalyzer"}])

        thresholds = policy_raw.get("fraud_thresholds", {})
        history = claim.get("claims_history") or []
        treatment_date = str(claim.get("treatment_date") or "")
        same_day = sum(1 for item in history if str(item.get("date")) == treatment_date)
        signals: List[Dict[str, Any]] = []
        if same_day >= int(thresholds.get("same_day_claims_limit", 9999)):
            signals.append({"type": "same_day_claims", "count": same_day})
        return FraudAnalysis(ok=not signals, manual_review=bool(signals), signals=signals)


class ConfidenceEngine:
    def score(self, state: ClaimState) -> ConfidenceResult:
        score = Decimal("0.90")
        factors: List[Dict[str, Any]] = [{"factor": "base", "value": "0.90"}]
        if state.get("degraded"):
            score = Decimal("0.60")
            factors.append({"factor": "degraded", "value": "-0.30"})
        if state.get("manual_review_reason"):
            score = min(score, Decimal("0.50"))
            factors.append({"factor": "manual_review", "value": "-0.40"})
        if state.get("blocked_reason"):
            score = Decimal("0.0")
            factors.append({"factor": "blocked", "value": "0"})
        return ConfidenceResult(score=score, factors=factors)


class DecisionEngine:
    def decide(self, state: ClaimState) -> DecisionResult:
        if state.get("blocked_reason"):
            return DecisionResult(
                decision=None,
                approved_amount=None,
                processing_status="BLOCKED_DOCUMENT",
                reason=str(state["blocked_reason"]),
                confidence_score=Decimal("0"),
            )

        if state.get("policy_rejection_reason"):
            return DecisionResult(
                decision="REJECTED",
                approved_amount=Decimal("0"),
                processing_status="COMPLETED",
                reason=str(state["policy_rejection_reason"]),
                confidence_score=state.get("confidence_result", ConfidenceResult(score=Decimal("0.90"))).score,
            )

        if state.get("manual_review_reason"):
            return DecisionResult(
                decision="MANUAL_REVIEW",
                approved_amount=Decimal("0"),
                processing_status="PENDING_MANUAL_REVIEW",
                reason=str(state["manual_review_reason"]),
                confidence_score=state.get("confidence_result", ConfidenceResult(score=Decimal("0.50"))).score,
            )

        financials = state.get("financials_result")
        approved_amount = financials.approved_amount if financials else Decimal("0")
        decision = financials.decision_hint if financials else "APPROVED"
        return DecisionResult(
            decision=decision,
            approved_amount=approved_amount,
            processing_status="COMPLETED",
            reason="approved by deterministic policy and financial engine",
            confidence_score=state.get("confidence_result", ConfidenceResult(score=Decimal("0.90"))).score,
        )


@dataclass
class ClaimWorkflow:
    policy_repo: PolicyRepository
    trace_manager: TraceManager
    policy_evaluator: PolicyEvaluator
    providers: Optional[ProviderSet] = None
    audit_repository: Optional[ClaimAuditRepository] = None

    def __post_init__(self) -> None:
        self.member_resolver = MemberResolver()
        self.production_documents = ProductionDocumentAdapter(self.providers)
        self.classifier = DocumentClassifier()
        self.verifier = DocumentVerifier()
        self.extractor = DocumentExtractor()
        self.consistency = ConsistencyAgent()
        self.member_doc_consistency = MemberDocumentConsistencyAgent()
        self.calculation = CalculationEngine()
        self.fraud = FraudAnalyzer()
        self.confidence = ConfidenceEngine()
        self.decision = DecisionEngine()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ClaimState)
        # Core pipeline nodes
        graph.add_node("input_validation", self._input_validation)
        graph.add_node("member_resolution", self._member_resolution)
        graph.add_node("document_classification", self._document_classification)
        graph.add_node("document_verification", self._document_verification)
        graph.add_node("blocked_document", self._blocked_document)
        graph.add_node("document_extraction", self._document_extraction)
        graph.add_node("member_document_consistency", self._member_document_consistency)
        graph.add_node("cross_document_consistency", self._cross_document_consistency)
        graph.add_node("policy_evaluation", self._policy_evaluation)
        graph.add_node("policy_rejection", self._policy_rejection)
        graph.add_node("financial_calculation", self._financial_calculation)
        graph.add_node("fraud_analysis", self._fraud_analysis)
        graph.add_node("manual_review", self._manual_review)
        graph.add_node("confidence", self._confidence)
        graph.add_node("final_decision", self._final_decision)

        graph.set_entry_point("input_validation")
        graph.add_edge("input_validation", "member_resolution")
        graph.add_conditional_edges(
            "member_resolution",
            self._route_after_member_resolution,
            {"blocked": "blocked_document", "continue": "document_classification"},
        )
        graph.add_edge("document_classification", "document_extraction")
        graph.add_edge("document_extraction", "document_verification")
        graph.add_conditional_edges(
            "document_verification",
            self._route_after_verification,
            {"blocked": "blocked_document", "continue": "member_document_consistency"},
        )
        graph.add_conditional_edges(
            "member_document_consistency",
            self._route_after_member_doc_consistency,
            {"blocked": "blocked_document", "continue": "cross_document_consistency"},
        )
        graph.add_conditional_edges(
            "cross_document_consistency", self._route_after_consistency,
            {"blocked": "blocked_document", "continue": "policy_evaluation"},
        )
        graph.add_conditional_edges(
            "policy_evaluation",
            self._route_after_policy,
            {"rejected": "policy_rejection", "continue": "financial_calculation"},
        )
        graph.add_edge("financial_calculation", "fraud_analysis")
        graph.add_conditional_edges(
            "fraud_analysis",
            self._route_after_fraud,
            {"manual_review": "manual_review", "continue": "confidence"},
        )
        graph.add_edge("confidence", "final_decision")
        graph.add_edge("final_decision", END)
        return graph.compile()

    def run(self, raw_claim: Dict[str, Any]) -> ClaimProcessingResult:
        claim_id = f"CLM-{uuid.uuid4().hex[:8]}"
        self.policy_repo.load()
        policy_raw = self.policy_repo.raw() or {}
        normalized_claim = normalize_claim_input(raw_claim)

        initial_state: ClaimState = {
            "claim_id": claim_id,
            "raw_claim": dict(raw_claim),
            "normalized_claim": normalized_claim,
            "policy_raw": policy_raw,
            "degraded": False,
            "component_failures": [],
        }
        final_state = self.graph.invoke(initial_state)
        result = final_state.get("result")
        if result is None:
            result = ClaimProcessingResult(
                claim_id=claim_id,
                decision=None,
                approved_amount=None,
                confidence_score=Decimal("0"),
                processing_status="BLOCKED",
                reason_code="DOCUMENT_VERIFICATION_FAILED",
                reason=str(final_state.get("blocked_reason") or "document verification failed"),
                degraded=bool(final_state.get("degraded", False)),
                trace=self.trace_manager.get_events_for_claim(claim_id),
            )
        if self.audit_repository is not None:
            self.audit_repository.persist_claim_bundle(claim_id, raw_claim, final_state, self.trace_manager.get_events_for_claim(claim_id))
        return result

    def _input_validation(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        claim = state["normalized_claim"]
        missing = [field for field in ("member_id", "policy_id", "claim_category", "treatment_date", "claimed_amount") if not claim.get(field)]
        if missing:
            reason = f"invalid input: missing {', '.join(missing)}"
            _trace_event(self.trace_manager, claim_id, "INPUT_VALIDATION", "ClaimIntake", "ERROR", safe_input={"missing": missing}, error=reason)
            state["blocked_reason"] = reason
            return state
        _trace_event(self.trace_manager, claim_id, "INPUT_VALIDATION", "ClaimIntake", "OK", safe_input={k: claim.get(k) for k in ("member_id", "policy_id", "claim_category", "treatment_date", "claimed_amount")})
        return state

    def _document_classification(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        documents = []
        for document in state["normalized_claim"].get("documents", []):
            try:
                documents.append(self.production_documents.materialize(document))
            except Exception as exc:
                state["blocked_reason"] = f"document extraction failed for {document.get('file_id')}: {exc}"
                state["component_failures"].append({"component": "DocumentExtraction", "severity": "CRITICAL", "reason": str(exc)})
                _trace_event(self.trace_manager, claim_id, "DOCUMENT_EXTRACTION", "ProductionDocumentAdapter", "ERROR", error=str(exc))
                return state
        state["prepared_documents"] = documents
        classifications = self.classifier.classify(documents)
        state["document_classifications"] = classifications
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_CLASSIFICATION", "DocumentClassifier", "OK", safe_output=[classification.model_dump(mode="python") for classification in classifications])
        return state

    def _member_resolution(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        res = self.member_resolver.resolve(state["normalized_claim"], state["policy_raw"])
        state["member_resolution_result"] = res
        _trace_event(self.trace_manager, claim_id, "MEMBER_RESOLUTION", "MemberResolver", "OK" if res.eligible else "ERROR", safe_output=res.model_dump(mode="python"))
        if not res.eligible:
            state["blocked_reason"] = "; ".join(res.errors)
        return state

    def _route_after_member_resolution(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _member_document_consistency(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        res = self.member_doc_consistency.check(state["member_resolution_result"], state.get("document_extractions_result", []))
        state["member_document_consistency_result"] = res
        summary = "Document patient identity matches the resolved policy member." if res.consistent else "; ".join(f"Resolved member {m.get('resolved_member')} does not match document patient {m.get('document_patient')}." for m in res.mismatches) + " Processing was blocked before policy evaluation."
        _trace_event(self.trace_manager, claim_id, "MEMBER_DOCUMENT_CONSISTENCY", "MemberDocumentConsistencyAgent", "PASSED" if res.consistent else "FAILED", safe_output=res.model_dump(mode="python"), summary=summary, reason_code=None if res.consistent else "DOCUMENT_VERIFICATION_FAILED")
        if not res.consistent:
            state["blocked_reason"] = "; ".join([m.get("reason", "mismatch") for m in res.mismatches])
        return state

    def _route_after_member_doc_consistency(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _document_verification(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        claim = state["normalized_claim"]
        classifications = state.get("document_classifications", [])
        verification = self.verifier.verify(claim, classifications, state["policy_raw"])
        state["document_verification_result"] = verification
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_QUALITY", "DocumentVerifier", "ERROR" if verification.unreadable else "OK", safe_output={"unreadable": verification.unreadable})
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_VERIFICATION", "DocumentVerifier", "PASSED" if verification.ok else "FAILED", safe_output=verification.model_dump(mode="python"), summary="All policy-required document types were present and readable." if verification.ok else verification.message + ". Claim adjudication was blocked.", reason_code=None if verification.ok else "DOCUMENT_VERIFICATION_FAILED")
        if not verification.ok:
            state["blocked_reason"] = verification.message
        return state

    def _route_after_verification(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _blocked_document(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("blocked_reason") or "blocked document")
        completed = {event.step for event in self.trace_manager.get_events_for_claim(claim_id)}
        blocker = next((stage for stage in ("MEMBER_DOCUMENT_CONSISTENCY", "CROSS_DOCUMENT_CONSISTENCY", "DOCUMENT_VERIFICATION", "MEMBER_RESOLUTION") if stage in completed), "DOCUMENT_VERIFICATION")
        for stage in ("POLICY_EVALUATION", "FINANCIAL_CALCULATION", "FRAUD_ANALYSIS", "CONFIDENCE"):
            if stage not in completed:
                _trace_event(self.trace_manager, claim_id, stage, "Workflow", "SKIPPED", summary=f"{stage.replace('_', ' ').title()} was skipped because {blocker.replace('_', ' ').lower()} failed.", reason_code="UPSTREAM_STAGE_FAILED", evidence={"blocked_by": blocker})
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "BLOCKED", safe_output={"decision": None, "reason": reason}, summary=f"Claim processing was blocked: {reason}", reason_code="DOCUMENT_VERIFICATION_FAILED")
        failures = state.get("component_failures") or []
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision=None,
            approved_amount=None,
            confidence_score=Decimal("0"),
            processing_status="BLOCKED",
            reason_code="DOCUMENT_VERIFICATION_FAILED",
            reason=reason,
            degraded=bool(state.get("degraded", False)),
            manual_review_recommended=bool(state.get("degraded", False)),
            component_failures=failures,
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["result"] = result
        return state

    def _document_extraction(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        documents = state.get("prepared_documents", [])
        extractions = self.extractor.extract(documents)
        state["document_extractions_result"] = extractions
        state["normalized_claim"]["documents"] = [document.model_dump(mode="python") for document in documents]
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_EXTRACTION", "DocumentExtractor", "OK", safe_output=[extraction.model_dump(mode="python") for extraction in extractions])
        return state

    def _cross_document_consistency(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        consistency = self.consistency.check(state.get("document_extractions_result", []))
        state["consistency_result"] = consistency
        _trace_event(self.trace_manager, claim_id, "CROSS_DOCUMENT_CONSISTENCY", "ConsistencyAgent", "PASSED" if consistency.ok else "FAILED", safe_output=consistency.model_dump(mode="python"), summary="Patient names, treatment dates, and bill arithmetic are consistent across the submitted documents." if consistency.ok else consistency.message + ". Processing was blocked before policy evaluation.", reason_code=None if consistency.ok else "DOCUMENT_VERIFICATION_FAILED")
        if not consistency.ok:
            state["blocked_reason"] = consistency.message
        return state

    def _route_after_consistency(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _policy_evaluation(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        evaluation = self.policy_evaluator.evaluate(state["normalized_claim"])
        state["policy_evaluation_result"] = evaluation
        _trace_event(self.trace_manager, claim_id, "POLICY_EVALUATION", "PolicyEvaluator", "OK", safe_output=evaluation.model_dump(mode="python"))
        failed = {check.name: check for check in evaluation.checks if not check.ok}
        if failed:
            # Every failed authoritative rule maps deterministically. Network status is
            # informational: non-network care is still covered without a discount.
            mappings = (
                ("member_exists", "MEMBER_INVALID"), ("member_eligibility", "MEMBER_INELIGIBLE"),
                ("policy_period", "POLICY_INVALID"), ("category_coverage", "CATEGORY_NOT_COVERED"),
                ("document_requirements", "DOCUMENT_REQUIREMENTS_NOT_MET"), ("waiting_periods", "WAITING_PERIOD"),
                ("exclusions", "EXCLUDED_CONDITION"), ("pre_authorization", "PRE_AUTH_MISSING"),
                ("annual_limit", "ANNUAL_LIMIT_EXCEEDED"), ("category_sub_limit", "CATEGORY_LIMIT_EXCEEDED"),
                ("per_claim_limit", "PER_CLAIM_EXCEEDED"), ("minimum_claim_amount", "MINIMUM_CLAIM_AMOUNT_NOT_MET"),
            )
            for check_name, reason in mappings:
                if check_name in failed and not (check_name == "per_claim_limit" and str(state["normalized_claim"].get("claim_category", "")).upper() == "DENTAL"):
                    state["policy_rejection_reason"] = reason
                    break
        return state

    def _route_after_policy(self, state: ClaimState) -> str:
        return "rejected" if state.get("policy_rejection_reason") else "continue"

    def _policy_rejection(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("policy_rejection_reason") or "policy rejection")
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output={"decision": "REJECTED", "reason": reason})
        failures = state.get("component_failures") or []
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision="REJECTED",
            approved_amount=Decimal("0"),
            confidence_score=Decimal("0.95"),
            processing_status="COMPLETED",
            degraded=bool(state.get("degraded", False)),
            manual_review_recommended=bool(state.get("degraded", False)),
            component_failures=failures,
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["result"] = result
        return state

    def _financial_calculation(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        financials = self.calculation.calculate(state["normalized_claim"], state["policy_raw"])
        state["financials_result"] = financials
        _trace_event(self.trace_manager, claim_id, "FINANCIAL_CALCULATION", "CalculationEngine", "OK", safe_output=financials.model_dump(mode="python"))
        return state

    def _fraud_analysis(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        fraud = self.fraud.analyze(state["normalized_claim"], state["policy_raw"])
        state["fraud_result"] = fraud
        if state["normalized_claim"].get("simulate_component_failure"):
            state["degraded"] = True
            failure_record = {"component": "FraudAnalyzer", "severity": "NON_CRITICAL", "reason": "simulated failure — fraud analysis skipped"}
            state.setdefault("component_failures", []).append(failure_record)
            # Trace the degradation clearly so it is visible in audit
            _trace_event(
                self.trace_manager, claim_id, "FRAUD_ANALYSIS", "FraudAnalyzer", "DEGRADED",
                safe_output={"ok": None, "manual_review": None, "signals": fraud.signals},
                error="component failure simulated — fraud analysis result is unreliable",
            )
        else:
            if fraud.manual_review:
                state["manual_review_reason"] = ", ".join(signal.get("type", "fraud_signal") for signal in fraud.signals) or "fraud signal"
            _trace_event(self.trace_manager, claim_id, "FRAUD_ANALYSIS", "FraudAnalyzer", "OK", safe_output=fraud.model_dump(mode="python"))
        if fraud.manual_review and not state["normalized_claim"].get("simulate_component_failure"):
            state["manual_review_reason"] = ", ".join(signal.get("type", "fraud_signal") for signal in fraud.signals) or "fraud signal"
        return state

    def _route_after_fraud(self, state: ClaimState) -> str:
        return "manual_review" if state.get("manual_review_reason") else "continue"

    def _manual_review(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("manual_review_reason") or "manual review")
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output={"decision": "MANUAL_REVIEW", "reason": reason})
        failures = state.get("component_failures") or []
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision="MANUAL_REVIEW",
            approved_amount=Decimal("0"),
            confidence_score=Decimal("0.50"),
            processing_status="PENDING_MANUAL_REVIEW",
            degraded=bool(state.get("degraded", False)),
            manual_review_recommended=True,
            component_failures=failures,
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["result"] = result
        return state

    def _confidence(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        confidence = self.confidence.score(state)
        state["confidence_result"] = confidence
        _trace_event(self.trace_manager, claim_id, "CONFIDENCE", "ConfidenceEngine", "OK", safe_output=confidence.model_dump(mode="python"))
        return state

    def _final_decision(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        decision = self.decision.decide(state)
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output=decision.model_dump(mode="python"))
        failures = state.get("component_failures") or []
        is_degraded = bool(state.get("degraded", False))
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision=decision.decision,
            approved_amount=decision.approved_amount,
            confidence_score=decision.confidence_score,
            processing_status=decision.processing_status,
            degraded=is_degraded,
            manual_review_recommended=is_degraded,
            component_failures=failures,
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["decision_result"] = decision
        state["result"] = result
        return state
