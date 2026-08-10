from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any, Dict
from decimal import Decimal


class DocumentArtifact(BaseModel):
    model_config = ConfigDict(extra="allow")

    file_id: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    # test-fixture adapter fields (allowed but not used in production classifier)
    actual_type: Optional[str] = None
    content: Optional[dict] = None


class StructuredDocumentData(BaseModel):
    """Validated, provider-neutral document understanding contract."""
    document_type: str = "UNKNOWN"
    patient_name: Optional[str] = None
    treatment_date: Optional[str] = None
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    total: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    other_charges: Optional[Decimal] = None
    grand_total: Optional[Decimal] = None
    amount_payable: Optional[Decimal] = None
    amount_received: Optional[Decimal] = None
    quality: str = "UNKNOWN"
    confidence: Decimal = Decimal("0.5")


class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: str
    claimed_amount: Decimal
    simulate_component_failure: Optional[bool] = False
    documents: List[DocumentArtifact] = Field(default_factory=list)


class PolicySnapshot(BaseModel):
    policy_id: str
    policy_name: Optional[str]
    insurer: Optional[str]
    coverage: Optional[Any]


class NormalizedDocument(BaseModel):
    file_id: str
    document_type: str
    quality: str = "UNKNOWN"
    extracted: Dict[str, Any] = Field(default_factory=dict)
    source: Dict[str, Any] = Field(default_factory=dict)


class DocumentClassification(BaseModel):
    file_id: str
    document_type: str
    confidence: Decimal = Decimal("0.5")
    quality: str = "UNKNOWN"
    signals: List[str] = Field(default_factory=list)


class DocumentVerificationResult(BaseModel):
    ok: bool
    status: str
    message: str
    required: List[str] = Field(default_factory=list)
    provided: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    unreadable: List[str] = Field(default_factory=list)
    wrong_type: List[str] = Field(default_factory=list)


class DocumentQualityResult(BaseModel):
    """Deterministic readability assessment, independent of type recognition."""
    file_id: str
    document_type: str
    quality: str
    reason: str
    missing_or_unreliable_fields: List[str] = Field(default_factory=list)


class DocumentExtraction(BaseModel):
    file_id: str
    document_type: str
    extracted: Dict[str, Any] = Field(default_factory=dict)
    confidence: Decimal = Decimal("0.5")


class MemberResolutionResult(BaseModel):
    member_id: str
    member_name: str
    member_found: bool
    policy_id: str
    policy_valid: bool
    eligible: bool
    dependents: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class MemberDocumentConsistencyResult(BaseModel):
    consistent: bool
    mismatches: List[Dict[str, Any]] = Field(default_factory=list)



class ConsistencyResult(BaseModel):
    ok: bool
    message: str
    found_names: List[str] = Field(default_factory=list)
    mismatches: List[Dict[str, Any]] = Field(default_factory=list)
    review_required: bool = False


class FinancialCalculationResult(BaseModel):
    approved_amount: Decimal
    decision_hint: str
    breakdown: Dict[str, Any] = Field(default_factory=dict)


class FraudAnalysis(BaseModel):
    ok: bool
    manual_review: bool = False
    signals: List[Dict[str, Any]] = Field(default_factory=list)


class ConfidenceResult(BaseModel):
    score: Decimal
    factors: List[Dict[str, Any]] = Field(default_factory=list)


class DecisionResult(BaseModel):
    decision: Optional[str]
    approved_amount: Optional[Decimal]
    processing_status: str
    reason: str
    confidence_score: Decimal
    decision_summary: str = ""


class TraceEvent(BaseModel):
    trace_id: str
    claim_id: Optional[str]
    step: str
    component: str
    status: str
    duration_ms: Optional[int]
    safe_input: Optional[Any]
    safe_output: Optional[Any]
    evidence: Optional[Any]
    error: Optional[str]
    summary: Optional[str] = None
    reason_code: Optional[str] = None


class ClaimProcessingResult(BaseModel):
    claim_id: str
    decision: Optional[str] = None
    approved_amount: Optional[Decimal] = None
    reimbursable_amount: Optional[Decimal] = None
    confidence_score: Optional[Decimal] = None
    processing_status: str = "RECEIVED"
    reason_code: Optional[str] = None
    reason: Optional[str] = None
    decision_summary: str = ""
    degraded: bool = False
    # Set True when the system recommends a human reviews the claim despite producing a decision.
    # This is required by the assignment for degraded/incomplete processing.
    manual_review_recommended: bool = False
    component_failures: List[Dict[str, Any]] = Field(default_factory=list)
    trace: List[TraceEvent] = Field(default_factory=list)


class RuleResult(BaseModel):
    name: str
    ok: bool
    details: Optional[dict]


class PolicyEvaluation(BaseModel):
    policy_id: str
    checks: List[RuleResult] = Field(default_factory=list)

