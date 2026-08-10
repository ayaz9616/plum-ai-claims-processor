from decimal import Decimal
from typing import Dict, Any
from backend.app.schemas import DecisionResult, ClaimProcessingResult, ConfidenceResult
from backend.app.workflow.state import ClaimState


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


