from decimal import Decimal
from typing import Dict, Any
from backend.app.schemas import ConfidenceResult, ClaimProcessingResult
from backend.app.workflow.state import ClaimState


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


