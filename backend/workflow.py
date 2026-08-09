from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .adapter import normalize_claim_input
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
    NormalizedDocument,
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
    document_classifications: List[DocumentClassification]
    document_verification_result: DocumentVerificationResult
    document_extractions_result: List[DocumentExtraction]
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
) -> None:
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
        ok = len(unique_names) <= 1
        message = "documents consistent"
        if not ok:
            message = f"patient names mismatch: {', '.join(unique_names)}"
        return ConsistencyResult(ok=ok, message=message, found_names=unique_names, mismatches=[] if ok else unique_names)


class CalculationEngine:
    def calculate(self, claim: Dict[str, Any], policy_raw: Dict[str, Any]) -> FinancialCalculationResult:
        category = str(claim.get("claim_category") or "").lower()
        category_policy = policy_raw.get("opd_categories", {}).get(category, {}) or {}
        claimed_amount = Decimal(str(claim.get("claimed_amount", 0)))

        if category.upper() == "DENTAL":
            approved_amount = Decimal("0")
            excluded = {str(item).lower() for item in category_policy.get("excluded_procedures", [])}
            covered = set()
            for document in claim.get("documents", []):
                for item in (document.get("extracted", {}) or {}).get("line_items", []) or []:
                    description = str(item.get("description") or "")
                    amount = Decimal(str(item.get("amount", 0)))
                    if any(exclusion in description.lower() for exclusion in excluded):
                        continue
                    approved_amount += amount
                    covered.add(description)
            breakdown = {"covered_line_items": sorted(covered), "excluded_procedures": sorted(excluded)}
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
    audit_repository: Optional[ClaimAuditRepository] = None

    def __post_init__(self) -> None:
        self.classifier = DocumentClassifier()
        self.verifier = DocumentVerifier()
        self.extractor = DocumentExtractor()
        self.consistency = ConsistencyAgent()
        self.calculation = CalculationEngine()
        self.fraud = FraudAnalyzer()
        self.confidence = ConfidenceEngine()
        self.decision = DecisionEngine()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ClaimState)
        graph.add_node("input_validation", self._input_validation)
        graph.add_node("document_classification", self._document_classification)
        graph.add_node("document_verification", self._document_verification)
        graph.add_node("blocked_document", self._blocked_document)
        graph.add_node("document_extraction", self._document_extraction)
        graph.add_node("cross_document_consistency", self._cross_document_consistency)
        graph.add_node("policy_evaluation", self._policy_evaluation)
        graph.add_node("policy_rejection", self._policy_rejection)
        graph.add_node("financial_calculation", self._financial_calculation)
        graph.add_node("fraud_analysis", self._fraud_analysis)
        graph.add_node("manual_review", self._manual_review)
        graph.add_node("confidence", self._confidence)
        graph.add_node("final_decision", self._final_decision)

        graph.set_entry_point("input_validation")
        graph.add_edge("input_validation", "document_classification")
        graph.add_edge("document_classification", "document_verification")
        graph.add_conditional_edges(
            "document_verification",
            self._route_after_verification,
            {"blocked": "blocked_document", "continue": "document_extraction"},
        )
        graph.add_conditional_edges("blocked_document", lambda _: "end", {"end": END})
        graph.add_edge("document_extraction", "cross_document_consistency")
        graph.add_conditional_edges(
            "cross_document_consistency",
            self._route_after_consistency,
            {"blocked": "blocked_document", "continue": "policy_evaluation"},
        )
        graph.add_conditional_edges(
            "policy_evaluation",
            self._route_after_policy,
            {"rejected": "policy_rejection", "continue": "financial_calculation"},
        )
        graph.add_conditional_edges("policy_rejection", lambda _: "end", {"end": END})
        graph.add_edge("financial_calculation", "fraud_analysis")
        graph.add_conditional_edges(
            "fraud_analysis",
            self._route_after_fraud,
            {"manual_review": "manual_review", "continue": "confidence"},
        )
        graph.add_conditional_edges("manual_review", lambda _: "end", {"end": END})
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
                processing_status="BLOCKED_DOCUMENT",
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
        documents = [NormalizedDocument(**document) for document in state["normalized_claim"].get("documents", [])]
        classifications = self.classifier.classify(documents)
        state["document_classifications"] = classifications
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_CLASSIFICATION", "DocumentClassifier", "OK", safe_output=[classification.model_dump(mode="python") for classification in classifications])
        return state

    def _document_verification(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        claim = state["normalized_claim"]
        classifications = state.get("document_classifications", [])
        verification = self.verifier.verify(claim, classifications, state["policy_raw"])
        state["document_verification_result"] = verification
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_VERIFICATION", "DocumentVerifier", "OK", safe_output=verification.model_dump(mode="python"))
        if not verification.ok:
            state["blocked_reason"] = verification.message
        return state

    def _route_after_verification(self, state: ClaimState) -> str:
        return "blocked" if state.get("blocked_reason") else "continue"

    def _blocked_document(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("blocked_reason") or "blocked document")
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output={"decision": None, "reason": reason})
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision=None,
            approved_amount=None,
            confidence_score=Decimal("0"),
            processing_status="BLOCKED_DOCUMENT",
            degraded=bool(state.get("degraded", False)),
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["result"] = result
        return state

    def _document_extraction(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        documents = [NormalizedDocument(**document) for document in state["normalized_claim"].get("documents", [])]
        extractions = self.extractor.extract(documents)
        state["document_extractions_result"] = extractions
        _trace_event(self.trace_manager, claim_id, "DOCUMENT_EXTRACTION", "DocumentExtractor", "OK", safe_output=[extraction.model_dump(mode="python") for extraction in extractions])
        return state

    def _cross_document_consistency(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        consistency = self.consistency.check(state.get("document_extractions_result", []))
        state["consistency_result"] = consistency
        _trace_event(self.trace_manager, claim_id, "CROSS_DOCUMENT_CONSISTENCY", "ConsistencyAgent", "OK", safe_output=consistency.model_dump(mode="python"))
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
            if "waiting_periods" in failed:
                state["policy_rejection_reason"] = "WAITING_PERIOD"
            elif "exclusions" in failed:
                state["policy_rejection_reason"] = "EXCLUDED_CONDITION"
            elif "pre_authorization" in failed and failed["pre_authorization"].details.get("required"):
                state["policy_rejection_reason"] = "PRE_AUTH_MISSING"
            elif "per_claim_limit" in failed and str(state["normalized_claim"].get("claim_category", "")).upper() != "DENTAL":
                state["policy_rejection_reason"] = "PER_CLAIM_EXCEEDED"
        return state

    def _route_after_policy(self, state: ClaimState) -> str:
        return "rejected" if state.get("policy_rejection_reason") else "continue"

    def _policy_rejection(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("policy_rejection_reason") or "policy rejection")
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output={"decision": "REJECTED", "reason": reason})
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision="REJECTED",
            approved_amount=Decimal("0"),
            confidence_score=Decimal("0.95"),
            processing_status="COMPLETED",
            degraded=bool(state.get("degraded", False)),
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
            state.setdefault("component_failures", []).append({"component": "FraudAnalyzer", "severity": "NON_CRITICAL", "reason": "simulated failure"})
        if fraud.manual_review:
            state["manual_review_reason"] = ", ".join(signal.get("type", "fraud_signal") for signal in fraud.signals) or "fraud signal"
        _trace_event(self.trace_manager, claim_id, "FRAUD_ANALYSIS", "FraudAnalyzer", "OK", safe_output=fraud.model_dump(mode="python"))
        return state

    def _route_after_fraud(self, state: ClaimState) -> str:
        return "manual_review" if state.get("manual_review_reason") else "continue"

    def _manual_review(self, state: ClaimState) -> ClaimState:
        claim_id = state["claim_id"]
        reason = str(state.get("manual_review_reason") or "manual review")
        _trace_event(self.trace_manager, claim_id, "DECISION", "DecisionEngine", "OK", safe_output={"decision": "MANUAL_REVIEW", "reason": reason})
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision="MANUAL_REVIEW",
            approved_amount=Decimal("0"),
            confidence_score=Decimal("0.50"),
            processing_status="PENDING_MANUAL_REVIEW",
            degraded=bool(state.get("degraded", False)),
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
        result = ClaimProcessingResult(
            claim_id=claim_id,
            decision=decision.decision,
            approved_amount=decision.approved_amount,
            confidence_score=decision.confidence_score,
            processing_status=decision.processing_status,
            degraded=bool(state.get("degraded", False)),
            trace=self.trace_manager.get_events_for_claim(claim_id),
        )
        state["decision_result"] = decision
        state["result"] = result
        return state