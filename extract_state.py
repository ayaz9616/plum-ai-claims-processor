import os

state_path = 'backend/app/workflow/state.py'
workflow_path = 'backend/workflow.py'
backup_path = 'backend/workflow_backup.py'

state_content = '''from typing import TypedDict, Dict, Any, List, Optional
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
'''

with open(state_path, 'w', encoding='utf-8') as f:
    f.write(state_content)

for wp in [workflow_path, backup_path]:
    if os.path.exists(wp):
        with open(wp, 'r', encoding='utf-8') as f:
            content = f.read()
        
        start = content.find('class ClaimState(TypedDict, total=False):')
        if start != -1:
            end = content.find('def _trace_event', start)
            if end != -1:
                content = content[:start] + content[end:]
        
        if 'from backend.app.workflow.state import ClaimState' not in content:
            content = 'from backend.app.workflow.state import ClaimState\n' + content
            
        with open(wp, 'w', encoding='utf-8') as f:
            f.write(content)
