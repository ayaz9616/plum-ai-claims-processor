import uuid
from decimal import Decimal
from .app.schemas import ClaimSubmission, ClaimProcessingResult
from backend.app.infrastructure.repositories import PolicyRepository
from backend.app.trace import TraceManager
from backend.app.config import config
from .app.errors import RepositoryError
from backend.app.core.policy import PolicyEvaluator
from typing import Dict, Any
from backend.app.workflow.graph import ClaimWorkflow
from backend.app.infrastructure.providers import ProviderSet
from backend.app.infrastructure.storage import ClaimAuditRepository


class ClaimOrchestrator:
    def __init__(self, policy_repo: PolicyRepository, trace_manager: TraceManager, providers: ProviderSet | None = None):
        self.policy_repo = policy_repo
        self.trace = trace_manager
        self.policy_evaluator = PolicyEvaluator(policy_repo)
        audit_repository = ClaimAuditRepository(config.database_url) if config.database_url else None
        if audit_repository is not None:
            audit_repository.initialize()
        self.workflow = ClaimWorkflow(policy_repo, trace_manager, self.policy_evaluator, providers=providers, audit_repository=audit_repository)

    def process_claim(self, submission: ClaimSubmission) -> ClaimProcessingResult:
        try:
            raw_claim = submission.model_dump(mode="python") if isinstance(submission, ClaimSubmission) else dict(submission)
            return self.workflow.run(raw_claim)
        except Exception as exc:
            raise RepositoryError(f"claim processing failed: {exc}")
