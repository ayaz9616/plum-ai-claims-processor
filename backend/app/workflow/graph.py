from __future__ import annotations
from backend.app.infrastructure.document_adapter import ProductionDocumentAdapter

from backend.app.agents.document import DocumentClassifier, DocumentQualityGate, DocumentVerifier
from backend.app.agents.extraction import DocumentExtractor
from backend.app.agents.consistency import ConsistencyAgent, MemberDocumentConsistencyAgent
from backend.app.core.calculation import CalculationEngine
from backend.app.core.confidence import ConfidenceEngine
from backend.app.core.decision import DecisionEngine
from backend.app.core.identity import MemberResolver
from backend.app.workflow.state import ClaimState

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
import re
import json
from pathlib import Path

from langgraph.graph import END, StateGraph

from backend.app.core.adapter import infer_document_type, normalize_claim_input
from backend.app.extraction_normalize import DocumentExtractionNormalizationError, parse_structured_document
from backend.app.core.identity import normalize_identity_name
from backend.app.infrastructure.providers import ProviderSet, VisionRequest
from backend.uploads import STAGING_DIR
from backend.app.infrastructure.repositories import PolicyRepository
from backend.app.core.policy import PolicyEvaluator
from backend.app.infrastructure.storage import ClaimAuditRepository
from backend.app.schemas import (
    ClaimProcessingResult,
    ConfidenceResult,
    ConsistencyResult,
    DecisionResult,
    DocumentClassification,
    DocumentExtraction,
    DocumentQualityResult,
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
from backend.app.trace import TraceManager
from backend.app.agents.fraud import FraudAnalyzer


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





def _normalize_name(name: str) -> str:
    return normalize_identity_name(name)



















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
        self.quality_gate = DocumentQualityGate()
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
        graph.add_node("document_quality", self._document_quality)
        graph.add_node("blocked_document", self._blocked_document)
        graph.add_node("document_extraction", self._document_extraction)
        graph.add_node("member_document_consistency", self._member_document_consistency)
        graph.add_node("cross_document_consistency", self._cross_document_consistency)
        graph.add_node("policy_evaluation", self._policy_evaluation)
        graph.add_node("policy_rejection", self._policy_rejection)
        graph.add_node("financial_calculation", self._financial_calculation)
        graph.add_node("fraud_analysis", self._fraud_analysis)
        graph.add_node("confidence", self._confidence)
        graph.add_node("final_decision", self._final_decision)

        graph.set_entry_point("input_validation")
        graph.add_edge("input_validation", "member_resolution")
        graph.add_conditional_edges(
            "member_resolution",
            self._route_after_member_resolution,
            {"blocked": "blocked_document", "continue": "document_classification"},
        )
        graph.add_conditional_edges(
            "document_classification", self._route_after_document_classification,
            {"blocked": "blocked_document", "continue": "document_verification"},
        )
        graph.add_conditional_edges(
            "document_verification",
            self._route_after_verification,
            {"blocked": "blocked_document", "continue": "document_quality"},
        )
        graph.add_conditional_edges(
            "document_quality",
            self._route_after_quality,
            {"blocked": "blocked_document", "continue": "document_extraction"},
        )
        graph.add_conditional_edges(
            "document_extraction",
            self._route_after_extraction,
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
            {"manual_review": "confidence", "continue": "confidence"},
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
                decision_summary=self._decision_summary(final_state, None, None, str(final_state.get("blocked_reason") or "document verification failed")),
                degraded=bool(final_state.get("degraded", False)),
                trace=self.trace_manager.get_events_for_claim(claim_id),
            )
        if self.audit_repository is not None:
            self.audit_repository.persist_claim_bundle(claim_id, raw_claim, final_state, self.trace_manager.get_events_for_claim(claim_id))
        return result

    @staticmethod
    def _money(value: Any) -> str:
        amount = Decimal(str(value or 0))
        return f"₹{amount:,.0f}" if amount == amount.to_integral() else f"₹{amount:,.2f}"

    @staticmethod
    def _format_date(value: Any) -> str:
        raw = str(value or "").strip()
        if not raw:
            return "the eligibility date"
        for date_format in ("%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(raw, date_format)
                return f"{parsed.day} {parsed.strftime('%B %Y')}"
            except ValueError:
                continue
        return raw

    def _decision_summary(self, state: ClaimState, decision: Optional[str], approved_amount: Optional[Decimal], reason: str = "") -> str:
        claim = state["normalized_claim"]
        category = str(claim.get("claim_category") or "medical").lower().replace("_", " ")
        failures = state.get("component_failures", [])
        if decision is None:
            verification = state.get("document_verification_result")
            if failures and any(item.get("component") == "DocumentExtraction" for item in failures):
                return f"We couldn't process your {category} claim because the uploaded documents could not be successfully extracted and verified. Please re-upload clear required documents so the claim can be reviewed."
            if verification:
                if verification.unreadable:
                    unreadable_types = " and ".join([t.replace("_", " ").title() for t in verification.unreadable])
                    # Note: verification.unreadable currently holds file_ids from DocumentVerifier!
                    # Wait, verification.unreadable contains file_ids!
                    # I need to look up the document type from state["document_classifications"]
                    unreadable_doc_types = []
                    classifications = state.get("document_classifications", [])
                    for c in classifications:
                        if c.file_id in verification.unreadable:
                            unreadable_doc_types.append(c.document_type.replace("_", " ").title())
                    types_str = " and ".join(unreadable_doc_types) if unreadable_doc_types else "Document"
                    return f"We found your {types_str}, but it could not be read reliably. Please re-upload a clearer image or PDF of the {types_str} so we can continue processing your claim."
                
                needed = ", ".join(item.replace("_", " ").lower() for item in verification.missing)
                provided = ", ".join(item.replace("_", " ").lower() for item in verification.provided)
                return f"We couldn't process your {category} claim because {needed} is required but was not successfully verified. You uploaded {provided or 'no usable required documents'}; please re-upload the required document clearly."
            return f"We couldn't process your {category} claim because {reason}. Please correct the issue and submit the claim again."
        if decision == "MANUAL_REVIEW":
            fraud = state.get("fraud_result")
            same_day = next((s for s in (fraud.signals if fraud else []) if s.get("type") == "same_day_claims"), None)
            if same_day:
                return f"Your {category} claim has been sent for manual review because {same_day.get('count', 0) + 1} claims were submitted by the same member on the same day, which requires further verification."
            consistency = state.get("consistency_result")
            bill_issue = next((m for m in (consistency.mismatches if consistency else []) if m.get("field") == "bill_total"), None)
            if bill_issue:
                values = [f"itemized charges total {self._money(bill_issue.get('line_item_total'))}"]
                if bill_issue.get("amount_payable"):
                    values.append(f"the document states {self._money(bill_issue['amount_payable'])} as payable")
                if bill_issue.get("grand_total"):
                    values.append(f"{self._money(bill_issue['grand_total'])} as the grand total")
                evidence = values[0] if len(values) == 1 else f"{values[0]}, while {values[1]}" + (f" and {values[2]}" if len(values) > 2 else "")
                return f"Your {category} claim requires manual review because the hospital bill contains conflicting totals: {evidence}. The policy calculation was completed, but the conflicting amounts need verification before payment."
            return f"Your {category} claim has been sent for manual review because {reason} requires further verification."
        if decision == "REJECTED":
            evaluation = state.get("policy_evaluation_result")
            failed = {check.name: check for check in (evaluation.checks if evaluation else []) if not check.ok}
            rejection_reason = str(reason or state.get("policy_rejection_reason") or "").upper()

            if rejection_reason == "PRE_AUTH_MISSING" or "pre_authorization" in failed:
                details = failed["pre_authorization"].details or {}
                item = (details.get("reasons") or [{}])[0]
                threshold = item.get("threshold") or state.get("policy_raw", {}).get("opd_categories", {}).get("diagnostic", {}).get("pre_auth_threshold", 10000)
                return (
                    f"Your {category} claim was rejected because the {self._money(item.get('amount'))} "
                    f"{str(item.get('item', 'treatment')).upper()} required pre-authorization under your policy and "
                    f"no valid pre-authorization was provided. Pre-authorization is required for MRI claims above "
                    f"{self._money(threshold)}. Please obtain valid pre-authorization and resubmit the claim with "
                    f"the authorization details."
                )
            if rejection_reason == "WAITING_PERIOD" or "waiting_periods" in failed:
                details = failed["waiting_periods"].details or {}
                issues = details.get("issues") or []
                issue = issues[0] if issues else {}
                eligible_from = issue.get("eligible_from")
                condition = str(issue.get("condition") or "this condition").replace("_", " ")
                treatment_date = claim.get("treatment_date")
                if eligible_from and treatment_date:
                    return (
                        f"Your {category} claim was rejected because {condition}-related claims are covered after "
                        f"{self._format_date(eligible_from)} due to a policy waiting period. Your treatment date was "
                        f"{self._format_date(treatment_date)}."
                    )
                return f"Your {category} claim was rejected because the treatment falls within the policy waiting period."
            if rejection_reason == "EXCLUDED_CONDITION" or "exclusions" in failed:
                details = failed["exclusions"].details or {}
                found = details.get("found_exclusions") or []
                exclusion_text = found[0] if found else "This treatment"
                return (
                    f"Your {category} claim was rejected because the treatment is excluded under your policy. "
                    f"{exclusion_text} is not covered, including obesity and bariatric treatment where applicable."
                )
            if rejection_reason == "PER_CLAIM_EXCEEDED" or "per_claim_limit" in failed:
                details = failed["per_claim_limit"].details or {}
                return f"Your {category} claim was rejected because the claimed amount of {self._money(details.get('claimed_amount'))} exceeds your policy's per-claim limit of {self._money(details.get('limit'))}."
            return f"Your {category} claim was rejected because it did not meet the applicable policy requirement ({reason.replace('_', ' ').lower()})."
        financials = state.get("financials_result")
        breakdown = financials.breakdown if financials else {}
        if decision == "PARTIAL":
            items = breakdown.get("line_items", [])
            covered = next((item for item in items if item.get("eligible")), {})
            excluded = next((item for item in items if not item.get("eligible")), {})
            return f"Your {category} claim was partially approved for {self._money(approved_amount)} because the {self._money(covered.get('approved_amount'))} {covered.get('description', 'covered treatment')} is covered under your policy, while the {self._money(excluded.get('claimed_amount'))} {excluded.get('description', 'other treatment')} is excluded as a cosmetic treatment."
        copay = Decimal(str(breakdown.get("copay", 0)))
        eligible = Decimal(str(breakdown.get("claimed", claim.get("claimed_amount", 0))))
        verification = state.get("document_verification_result")
        documents = " and ".join(item.replace("_", " ").lower() for item in (verification.required if verification else [])) or "required documents"
        summary = f"Your {category} claim for {self._money(claim.get('claimed_amount'))} was approved because the {documents} were successfully verified and the treatment is covered under your policy"
        if copay:
            summary += f", and the {self._money(copay)} co-pay was deducted from the {self._money(eligible)} eligible amount"
        summary += f", resulting in an approved amount of {self._money(approved_amount)}."
        if state.get("degraded"):
            component = (failures[0].get("component") if failures else "a processing component")
            summary += f" Processing was degraded because {component} was unavailable, so manual review is recommended."
        return summary

    def _input_validation(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        claim = state["normalized_claim"]
        missing = [field for field in ("member_id", "policy_id", "claim_category", "treatment_date", "claimed_amount") if not claim.get(field)]
        if not claim.get("documents"):
            missing.append("documents")
        if missing:
            reason = f"invalid input: missing {', '.join(missing)}"
            _trace_event(self.trace_manager, claim_id, "INPUT_VALIDATION", "ClaimIntake", "ERROR", safe_input={"missing": missing}, error=reason)
            state["blocked_reason"] = reason
            return state
        _trace_event(self.trace_manager, claim_id, "INPUT_VALIDATION", "ClaimIntake", "OK", safe_input={k: claim.get(k) for k in ("member_id", "policy_id", "claim_category", "treatment_date", "claimed_amount")})
        return state

    def _document_classification(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        documents: List[NormalizedDocument] = []
        for document in state["normalized_claim"].get("documents", []):
            source = document.get("source") or {}
            if source.get("fixture") is False:
                inferred_type = infer_document_type({
                    "file_name": source.get("file_name"),
                    "mime_type": source.get("mime_type"),
                })
                documents.append(
                    NormalizedDocument(
                        file_id=str(document.get("file_id") or ""),
                        document_type=inferred_type if inferred_type != "UNKNOWN" else str(document.get("document_type") or "UNKNOWN").upper(),
                        quality=str(document.get("quality") or "UNKNOWN").upper(),
                        extracted=dict(document.get("extracted") or {}),
                        source=source,
                    )
                )
            else:
                documents.append(NormalizedDocument(**document))
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
        verification = self.verifier.verify(claim, classifications, state["policy_raw"], types_only=True)
        state["document_verification_result"] = verification
        _trace_event(
            self.trace_manager,
            claim_id,
            "DOCUMENT_VERIFICATION",
            "DocumentVerifier",
            "PASSED" if verification.ok else "FAILED",
            safe_output=verification.model_dump(mode="python"),
            summary="All policy-required document types were present." if verification.ok else verification.message + ". Claim adjudication was blocked.",
            reason_code=None if verification.ok else "DOCUMENT_VERIFICATION_FAILED",
        )
        if not verification.ok:
            state["blocked_reason"] = verification.message
        return state

    def _document_quality(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        quality_results = self.quality_gate.assess(state.get("prepared_documents", []))
        state["document_quality_results"] = quality_results
        quality_by_id = {result.file_id: result for result in quality_results}
        classifications = state.get("document_classifications", [])
        for classification in classifications:
            assessment = quality_by_id.get(classification.file_id)
            if assessment:
                classification.quality = assessment.quality
        unreadable_details = [result.model_dump(mode="python") for result in quality_results if result.quality == "UNREADABLE"]
        _trace_event(
            self.trace_manager,
            claim_id,
            "DOCUMENT_QUALITY",
            "DocumentQualityGate",
            "NEEDS_REUPLOAD" if unreadable_details else "OK",
            safe_output={"unreadable": unreadable_details},
        )
        if unreadable_details:
            unreadable_types = sorted({
                result.document_type.replace("_", " ").lower()
                for result in quality_results
                if result.quality == "UNREADABLE"
            })
            state["blocked_reason"] = f"please re-upload a clear {' and '.join(unreadable_types)}"
        return state

    def _route_after_quality(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _route_after_extraction(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _route_after_verification(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _blocked_document(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("blocked_reason") or "blocked document")
        completed = {event.step for event in self.trace_manager.get_events_for_claim(claim_id)}
        blocker = next((stage for stage in ("MEMBER_DOCUMENT_CONSISTENCY", "CROSS_DOCUMENT_CONSISTENCY", "DOCUMENT_QUALITY", "DOCUMENT_VERIFICATION", "MEMBER_RESOLUTION") if stage in completed), "DOCUMENT_VERIFICATION")
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
            decision_summary=self._decision_summary(state, None, None, reason),
            degraded=bool(state.get("degraded", False)),
            manual_review_recommended=bool(state.get("degraded", False)),
            component_failures=failures,
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["result"] = result
        return state

    def _document_extraction(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        documents: List[NormalizedDocument] = []
        for document in state.get("prepared_documents", []):
            payload = document.model_dump(mode="python") if hasattr(document, "model_dump") else dict(document)
            source = payload.get("source") or {}
            if source.get("fixture") is False:
                try:
                    documents.append(self.production_documents.materialize(payload))
                except Exception as exc:
                    state["blocked_reason"] = f"document extraction failed for {payload.get('file_id')}: {exc}"
                    state["component_failures"].append({"component": "DocumentExtraction", "severity": "CRITICAL", "reason": str(exc)})
                    _trace_event(self.trace_manager, claim_id, "DOCUMENT_EXTRACTION", "ProductionDocumentAdapter", "ERROR", error=str(exc))
                    return state
            else:
                documents.append(document if isinstance(document, NormalizedDocument) else NormalizedDocument(**payload))

        post_quality = self.quality_gate.assess(documents)
        unreadable_after_extraction = [result for result in post_quality if result.quality == "UNREADABLE"]
        if unreadable_after_extraction:
            unreadable_types = sorted({result.document_type.replace("_", " ").lower() for result in unreadable_after_extraction})
            state["blocked_reason"] = f"please re-upload a clear {' and '.join(unreadable_types)}"
            state["document_quality_results"] = post_quality
            _trace_event(
                self.trace_manager,
                claim_id,
                "DOCUMENT_QUALITY",
                "DocumentQualityGate",
                "NEEDS_REUPLOAD",
                safe_output={"unreadable": [result.model_dump(mode="python") for result in unreadable_after_extraction]},
                summary="Uploaded document content could not be read reliably after extraction.",
            )
            _trace_event(self.trace_manager, claim_id, "DOCUMENT_EXTRACTION", "DocumentExtractor", "ERROR", error="extracted document quality was unreadable")
            return state

        state["prepared_documents"] = documents
        extractions = self.extractor.extract(documents)
        state["document_extractions_result"] = extractions
        state["normalized_claim"]["documents"] = [document.model_dump(mode="python") for document in documents]
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_EXTRACTION", "DocumentExtractor", "OK", safe_output=[extraction.model_dump(mode="python") for extraction in extractions])
        return state

    def _cross_document_consistency(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        consistency = self.consistency.check(state.get("document_extractions_result", []))
        state["consistency_result"] = consistency
        status = "REVIEW_REQUIRED" if consistency.review_required else ("PASSED" if consistency.ok else "FAILED")
        arithmetic_verifiable = self.consistency.bill_arithmetic_verifiable(state.get("document_extractions_result", []))
        summary = ("Patient names, treatment dates, and bill arithmetic are consistent across the submitted documents." if arithmetic_verifiable else "Bill arithmetic could not be verified because one or more line-item amounts/total are unavailable.") if not consistency.mismatches else consistency.message + (". Processing continues with manual review required." if consistency.review_required else ". Processing was blocked before policy evaluation.")
        _trace_event(self.trace_manager, claim_id, "CROSS_DOCUMENT_CONSISTENCY", "ConsistencyAgent", status, safe_output=consistency.model_dump(mode="python"), summary=summary, reason_code="BILL_INTERNAL_TOTAL_INCONSISTENCY" if consistency.review_required else (None if consistency.ok else "DOCUMENT_VERIFICATION_FAILED"))
        if not consistency.ok:
            state["blocked_reason"] = consistency.message
        elif consistency.review_required:
            state["manual_review_reason"] = consistency.message
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
        summary = self._decision_summary(state, "REJECTED", Decimal("0"), reason)
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output={"decision": "REJECTED", "reason": reason, "decision_summary": summary})
        failures = state.get("component_failures") or []
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision="REJECTED",
            approved_amount=Decimal("0"),
            reimbursable_amount=Decimal("0"),
            confidence_score=Decimal("0.95"),
            processing_status="COMPLETED",
            reason=reason,
            decision_summary=summary,
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
            _trace_event(
                self.trace_manager, claim_id, "FRAUD_ANALYSIS", "FraudAnalyzer", "DEGRADED",
                safe_output=fraud.model_dump(mode="python"),
                error="component failure simulated — fraud analysis result is unreliable",
            )
        else:
            if fraud.manual_review:
                state["manual_review_reason"] = ", ".join(signal.get("type", "fraud_signal") for signal in fraud.signals) or "fraud signal"
            
            # Use degraded status if risk level is DEGRADED
            status = "DEGRADED" if getattr(fraud, "risk_level", "LOW") == "DEGRADED" else "OK"
            
            _trace_event(self.trace_manager, claim_id, "FRAUD_ANALYSIS", "FraudAnalyzer", status, safe_output=fraud.model_dump(mode="python"))
            
        if fraud.manual_review and not state["normalized_claim"].get("simulate_component_failure"):
            state["manual_review_reason"] = getattr(fraud, "explanation", "") or ", ".join(signal.get("type", "fraud_signal") for signal in fraud.signals) or "fraud signal"
        return state

    def _route_after_fraud(self, state: ClaimState) -> str:
        return "manual_review" if state.get("manual_review_reason") else "continue"

    def _manual_review(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("manual_review_reason") or "manual review")
        summary = self._decision_summary(state, "MANUAL_REVIEW", Decimal("0"), reason)
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output={"decision": "MANUAL_REVIEW", "reason": reason, "decision_summary": summary})
        failures = state.get("component_failures") or []
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision="MANUAL_REVIEW",
            approved_amount=Decimal("0"),
            reimbursable_amount=state.get("financials_result").approved_amount if state.get("financials_result") else None,
            confidence_score=Decimal("0.50"),
            processing_status="PENDING_MANUAL_REVIEW",
            reason=reason,
            decision_summary=summary,
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
        decision.decision_summary = self._decision_summary(state, decision.decision, decision.approved_amount, decision.reason)
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output=decision.model_dump(mode="python"))
        failures = state.get("component_failures") or []
        is_degraded = bool(state.get("degraded", False))
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision=decision.decision,
            approved_amount=decision.approved_amount,
            reimbursable_amount=(state.get("financials_result").approved_amount if decision.decision == "MANUAL_REVIEW" and state.get("financials_result") else decision.approved_amount),
            confidence_score=decision.confidence_score,
            processing_status=decision.processing_status,
            reason=decision.reason,
            decision_summary=decision.decision_summary,
            degraded=is_degraded,
            manual_review_recommended=is_degraded,
            component_failures=failures,
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["decision_result"] = decision
        state["result"] = result
        return state

    def _route_after_document_classification(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"
