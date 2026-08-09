import uuid
from decimal import Decimal
from .schemas import ClaimSubmission, ClaimProcessingResult
from .policy import PolicyRepository
from .trace import TraceManager
from .config import config
from .errors import RepositoryError
from .policy_evaluator import PolicyEvaluator
from typing import Dict, Any
from .workflow import ClaimWorkflow
from .storage import ClaimAuditRepository


def _apply_financials(claim: Dict[str, Any], policy_raw: Dict[str, Any], category_policy: Dict[str, Any]) -> Dict[str, Any]:
    from .workflow import CalculationEngine

    engine = CalculationEngine()
    result = engine.calculate(claim, policy_raw)
    return {"approved_amount": result.approved_amount, "breakdown": result.breakdown}


class ClaimOrchestrator:
    def __init__(self, policy_repo: PolicyRepository, trace_manager: TraceManager):
        self.policy_repo = policy_repo
        self.trace = trace_manager
        self.policy_evaluator = PolicyEvaluator(policy_repo)
        audit_repository = ClaimAuditRepository(config.database_url) if config.database_url else None
        if audit_repository is not None:
            audit_repository.initialize()
        self.workflow = ClaimWorkflow(policy_repo, trace_manager, self.policy_evaluator, audit_repository=audit_repository)

    def process_claim(self, submission: ClaimSubmission) -> ClaimProcessingResult:
        try:
            raw_claim = submission.model_dump(mode="python") if isinstance(submission, ClaimSubmission) else dict(submission)
            return self.workflow.run(raw_claim)
        except Exception as exc:
            raise RepositoryError(f"claim processing failed: {exc}")
