from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from decimal import Decimal


class DocumentArtifact(BaseModel):
    file_id: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    # test-fixture adapter fields (allowed but not used in production classifier)
    actual_type: Optional[str] = None
    content: Optional[dict] = None

    class Config:
        extra = "allow"


class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: str
    claimed_amount: Decimal
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


class DocumentExtraction(BaseModel):
    file_id: str
    document_type: str
    extracted: Dict[str, Any] = Field(default_factory=dict)
    confidence: Decimal = Decimal("0.5")


class ConsistencyResult(BaseModel):
    ok: bool
    message: str
    found_names: List[str] = Field(default_factory=list)
    mismatches: List[str] = Field(default_factory=list)


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


class ClaimProcessingResult(BaseModel):
    claim_id: str
    decision: Optional[str] = None
    approved_amount: Optional[Decimal] = None
    confidence_score: Optional[Decimal] = None
    processing_status: str = "RECEIVED"
    degraded: bool = False
    trace: List[TraceEvent] = Field(default_factory=list)


class RuleResult(BaseModel):
    name: str
    ok: bool
    details: Optional[dict]


class PolicyEvaluation(BaseModel):
    policy_id: str
    checks: List[RuleResult] = Field(default_factory=list)

