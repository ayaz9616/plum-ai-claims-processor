from typing import TypedDict, Dict, Any, List, Optional
from backend.app.schemas import (
    PolicyEvaluation,
    MemberResolutionResult,
    MemberDocumentConsistencyResult,
    DocumentClassification,
    DocumentVerificationResult,
    DocumentExtraction,
    DocumentQualityResult,
    NormalizedDocument,
    ConsistencyResult,
    FinancialCalculationResult,
    FraudAnalysis,
    ConfidenceResult,
    DecisionResult,
    ClaimProcessingResult
)

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
    document_quality_results: List[DocumentQualityResult]
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
