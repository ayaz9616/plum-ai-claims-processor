# Plum Claims AI — Component Contracts

> **AI-powered Health Insurance Claims Processing System**
> **Deliverable:** Component Contracts
> **Purpose:** Define precise interfaces between the significant components of the claims-processing pipeline so that an engineer can reimplement any component without reading its internal implementation.

---

## 1. Contract Philosophy

The system is organized around explicit component boundaries.

Each significant component has:

1. **Responsibility** — what the component owns.
2. **Input contract** — the data it accepts.
3. **Output contract** — the data it produces.
4. **Errors** — failures it can raise or report.
5. **Side effects** — database, AI-provider, or external interactions.
6. **Invariants** — properties downstream components can rely on.
7. **Failure behavior** — whether the pipeline stops or continues in a degraded state.

The most important architectural boundary is:

```text
                    Unstructured / Probabilistic
                              │
                              ▼
                     ┌─────────────────┐
                     │    Document AI  │
                     └────────┬────────┘
                              │
                              ▼
                     Structured Evidence
                              │
                              ▼
                    ┌────────────────────┐
                    │ Deterministic Core │
                    └─────────┬──────────┘
                              │
                              ▼
                     Decision + Trace
```

AI components are responsible for **interpreting evidence**.

Deterministic components are responsible for **enforcing policy, performing calculations and producing reproducible decisions**.
---

# 2. Shared Contract Conventions

## 2.1 Identifiers

All entities should use stable identifiers.

```text
claim_id
member_id
policy_id
document_id
trace_id
processing_id
```

Identifiers are opaque strings from the perspective of individual components.

A component must not infer business meaning from the identifier itself.

---

## 2.2 Dates

Dates use ISO-8601 calendar format:

```text
YYYY-MM-DD
```

Example:

```text
2024-11-01
```

Date arithmetic for waiting periods must use calendar-date semantics rather than string comparison.

---

## 2.3 Money

Monetary values represent INR.

For calculations, use:

```text
Decimal
```

or an equivalent exact-money representation.

Do not use binary floating-point arithmetic for financial calculations.

Example:

```json
{
 "currency": "INR",
 "amount": "4500.00"
}
```

---

## 2.4 Confidence

Confidence is represented as a normalized value:

```text
0.0 <= confidence <= 1.0
```

A confidence value is not permission for a component to ignore a deterministic failure.

For example:

```text
confidence = 0.95
```

does not override:

```text
WAITING_PERIOD_FAILED
```

---

## 2.5 Component Status

Components use one of:

```text
SUCCESS
DEGRADED
BLOCKED
FAILED
SKIPPED
```

### SUCCESS

The component completed normally.

### DEGRADED

The component completed with reduced evidence or a non-critical failure.

### BLOCKED

The component found a condition that prevents safe continuation.

### FAILED

The component could not complete its work.

### SKIPPED

The component was intentionally not executed because a previous stage made it unnecessary.

---

# 3. Core Domain Types

These types form the shared vocabulary between components.

---

## 3.1 ClaimSubmission

Represents the incoming claim.

```json
{
 "claim_id": "CLM_0042",
 "member_id": "EMP001",
 "policy_id": "PLUM_GHI_2024",
 "claim_category": "CONSULTATION",
 "treatment_date": "2024-11-01",
 "claimed_amount": "1500.00",
 "documents": [
 {
 "document_id": "DOC_001",
 "file_name": "prescription.jpg",
 "content_type": "image/jpeg"
 }
 ]
}
```

### Required fields

| Field | Type | Required |
|---|---|---:|
| `claim_id` | string | Yes |
| `member_id` | string | Yes |
| `policy_id` | string | Yes |
| `claim_category` | enum | Yes |
| `treatment_date` | date | Yes |
| `claimed_amount` | Decimal | Yes |
| `documents` | array | Yes |

### Claim category enum

```text
CONSULTATION
DIAGNOSTIC
PHARMACY
DENTAL
VISION
ALTERNATIVE_MEDICINE
```

---

# 4. Claim Orchestrator

## Responsibility

The Claim Orchestrator owns the lifecycle of a claim.

It coordinates the individual components but does not implement their internal business logic.

---

## Interface

```text
process_claim(claim: ClaimSubmission) -> ClaimProcessingResult
```

---

## Input

```text
ClaimSubmission
```

The orchestrator expects:

- valid claim identifier;
- member identifier;
- policy identifier;
- treatment category;
- treatment date;
- claimed amount;
- one or more documents.

---

## Output

```json
{
 "claim_id": "CLM_0042",
 "status": "COMPLETED",
 "decision": {
 "status": "APPROVED",
 "approved_amount": "1350.00",
 "currency": "INR"
 },
 "confidence": 0.94,
 "degraded": false,
 "failed_components": [],
 "trace_id": "TR_0042"
}
```

---

## Errors

```text
INVALID_CLAIM
INVALID_DOCUMENT_INPUT
ORCHESTRATION_ERROR
PERSISTENCE_ERROR
```

Component-specific failures should normally be captured as structured processing results rather than escaping as an unhandled server error.

---

## Invariants

The orchestrator guarantees:

- no final decision is produced before required-document verification;
- blocking document errors stop adjudication;
- deterministic policy evaluation occurs before final decision;
- financial calculation is isolated from LLM-generated arithmetic;
- component failures are visible in the final result;
- trace information is retained.

---

# 5. Input Validation Component

## Responsibility

Validate the structural correctness of a claim before expensive processing begins.

This component performs cheap deterministic validation.

---

## Interface

```text
validate_claim(claim: ClaimSubmission) -> ValidationResult
```

---

## Input

```text
ClaimSubmission
```

---

## Output

```json
{
 "valid": true,
 "errors": [],
 "warnings": []
}
```

Failure example:

```json
{
 "valid": false,
 "errors": [
 {
 "code": "INVALID_CLAIM_AMOUNT",
 "message": "Claimed amount must be greater than zero."
 }
 ],
 "warnings": []
}
```

---

## Validation rules

At minimum:

```text
claim_id exists
member_id exists
policy_id exists
claim_category is supported
treatment_date is valid
claimed_amount > 0
documents is non-empty
document metadata is valid
```

---

## Errors

```text
INVALID_CLAIM_ID
INVALID_MEMBER_ID
INVALID_POLICY_ID
INVALID_CATEGORY
INVALID_DATE
INVALID_AMOUNT
NO_DOCUMENTS
INVALID_FILE_METADATA
UNSUPPORTED_FILE_TYPE
FILE_TOO_LARGE
```

---

## Side Effects

None.

This component should remain deterministic and side-effect free.

---

# 6. Document Storage / Input Adapter

## Responsibility

Provide a normalized representation of uploaded images/PDFs to document-processing components.

The adapter abstracts where the temporary document comes from.

---

## Interface

```text
load_document(document_ref: DocumentReference) -> DocumentArtifact
```

---

## Input

```json
{
 "document_id": "DOC_001",
 "file_name": "prescription.jpg",
 "content_type": "image/jpeg",
 "source": "upload"
}
```

---

## Output

```text
DocumentArtifact
```

Conceptually:

```json
{
 "document_id": "DOC_001",
 "file_name": "prescription.jpg",
 "content_type": "image/jpeg",
 "bytes": "<binary document>",
 "page_count": 1
}
```

---

## Errors

```text
DOCUMENT_NOT_FOUND
DOCUMENT_READ_ERROR
UNSUPPORTED_MEDIA_TYPE
DOCUMENT_TOO_LARGE
CORRUPTED_DOCUMENT
```

---

## Side Effects

The implementation may interact with temporary file storage or object storage.

The domain layer should not depend on the storage implementation.

---

# 7. Document AI / Vision Provider

## Responsibility

Interpret an uploaded medical document and return structured evidence.

This is the primary probabilistic component.

It may use:

- OCR;
- multimodal vision;
- LLM extraction;
- document classification;
- normalization.

---

## Provider Interface

```text
analyze_document(
 document: DocumentArtifact,
 expected_category: ClaimCategory | None
) -> DocumentAnalysis
```

---

## Input

```text
DocumentArtifact
expected_category
```

`expected_category` is optional because document classification may happen before the exact required document type is known.

---

## Output

```json
{
 "document_id": "DOC_001",
 "document_type": "PRESCRIPTION",
 "quality": "GOOD",
 "confidence": 0.94,
 "fields": {
 "patient_name": "Rajesh Kumar",
 "date": "2024-11-01",
 "doctor_name": "Dr. Arun Sharma",
 "doctor_registration": "KA/45678/2015",
 "diagnosis": "Viral Fever",
 "medicines": [
 "Paracetamol 650mg",
 "Vitamin C 500mg"
 ]
 },
 "warnings": []
}
```

---

## Supported document types

```text
PRESCRIPTION
HOSPITAL_BILL
LAB_REPORT
PHARMACY_BILL
DENTAL_REPORT
OTHER
UNKNOWN
```

The supplied document guide describes prescriptions, hospital/clinic invoices, diagnostic/lab reports and pharmacy bills as the primary document types.

---

## Quality values

```text
GOOD
DEGRADED
UNREADABLE
```

---

## Errors

```text
VISION_PROVIDER_TIMEOUT
VISION_PROVIDER_UNAVAILABLE
INVALID_PROVIDER_RESPONSE
DOCUMENT_UNREADABLE
DOCUMENT_PROCESSING_ERROR
MODEL_OUTPUT_VALIDATION_ERROR
```

---

## Failure behavior

A provider failure is not automatically a claim rejection.

The orchestrator decides whether the failed analysis is:

```text
BLOCKING
```

or:

```text
NON_BLOCKING / DEGRADED
```

based on whether the missing evidence is necessary for a safe decision.

---

## Invariants

The provider must never return an unvalidated free-form object to the deterministic domain layer.

Its output must conform to the `DocumentAnalysis` schema.

---

# 8. Document Classification Component

## Responsibility

Determine the actual document type.

---

## Interface

```text
classify_document(
 analysis: DocumentAnalysis
) -> DocumentClassification
```

---

## Input

```text
DocumentAnalysis
```

---

## Output

```json
{
 "document_id": "DOC_001",
 "detected_type": "PRESCRIPTION",
 "confidence": 0.96,
 "status": "SUCCESS"
}
```

---

## Errors

```text
UNKNOWN_DOCUMENT_TYPE
LOW_CLASSIFICATION_CONFIDENCE
INVALID_DOCUMENT_ANALYSIS
```

---

## Invariant

The component must not silently convert:

```text
UNKNOWN
```

into a valid document type.

Low-confidence classification must remain visible.

---

# 9. Document Verification Component

## Responsibility

Verify that the uploaded documents satisfy the document requirements for the selected claim category.

This is an early pipeline gate.

---

## Interface

```text
verify_documents(
 claim_category: ClaimCategory,
 documents: list[DocumentAnalysis],
 policy: Policy
) -> DocumentVerificationResult
```

---

## Input

```text
claim_category
documents
policy
```

---

## Output

Successful example:

```json
{
 "status": "PASSED",
 "required": [
 "PRESCRIPTION",
 "HOSPITAL_BILL"
 ],
 "received": [
 "PRESCRIPTION",
 "HOSPITAL_BILL"
 ],
 "missing": [],
 "unexpected": [],
 "message": null
}
```

Failure example:

```json
{
 "status": "BLOCKED",
 "required": [
 "PRESCRIPTION",
 "HOSPITAL_BILL"
 ],
 "received": [
 "PRESCRIPTION",
 "PRESCRIPTION"
 ],
 "missing": [
 "HOSPITAL_BILL"
 ],
 "unexpected": [],
 "message": "Two prescriptions were uploaded, but a hospital bill is required for a consultation claim."
}
```

---

## Errors

```text
DOCUMENT_REQUIREMENT_NOT_FOUND
DOCUMENT_CLASSIFICATION_UNAVAILABLE
DOCUMENT_VERIFICATION_ERROR
```

---

## Blocking conditions

```text
required document missing
wrong document type uploaded
required document unreadable
document type cannot be established safely
```

---

## Invariant

No downstream claim adjudication should occur when a required document is missing or cannot be reliably interpreted.

---

# 10. Document Extraction / Normalization Component

## Responsibility

Convert document-specific extraction into normalized domain fields.

---

## Interface

```text
normalize_extraction(
 analysis: DocumentAnalysis
) -> NormalizedDocument
```

---

## Input

```text
DocumentAnalysis
```

---

## Output

```json
{
 "document_id": "DOC_001",
 "document_type": "HOSPITAL_BILL",
 "patient_name": "Rajesh Kumar",
 "document_date": "2024-11-01",
 "provider_name": "City Clinic, Bengaluru",
 "doctor_name": null,
 "diagnosis": null,
 "line_items": [
 {
 "description": "Consultation Fee",
 "amount": "1000.00"
 },
 {
 "description": "CBC Test",
 "amount": "300.00"
 }
 ],
 "total_amount": "1500.00",
 "quality": "GOOD",
 "confidence": 0.93
}
```

---

## Normalization rules

The component should:

- normalize field names;
- normalize dates;
- normalize amounts;
- normalize document types;
- preserve uncertain fields as uncertain;
- preserve missing fields as missing;
- avoid inventing values.

---

## Errors

```text
INVALID_EXTRACTION
INVALID_DATE_FIELD
INVALID_AMOUNT_FIELD
NORMALIZATION_ERROR
```

---

# 11. Cross-Document Consistency Component

## Responsibility

Compare extracted information across documents and against the claim.

---

## Interface

```text
check_consistency(
 claim: ClaimSubmission,
 documents: list[NormalizedDocument]
) -> ConsistencyResult
```

---

## Input

```text
ClaimSubmission
NormalizedDocument[]
```

---

## Output

```json
{
 "status": "PASSED",
 "checks": [
 {
 "check": "PATIENT_NAME",
 "status": "PASSED"
 },
 {
 "check": "TREATMENT_DATE",
 "status": "PASSED"
 }
 ],
 "mismatches": [],
 "confidence": 0.97
}
```

Mismatch example:

```json
{
 "status": "BLOCKED",
 "mismatches": [
 {
 "field": "patient_name",
 "document_a": {
 "document_id": "DOC_001",
 "value": "Rajesh Kumar"
 },
 "document_b": {
 "document_id": "DOC_002",
 "value": "Arjun Mehta"
 }
 }
 ],
 "message": "The prescription is for Rajesh Kumar, while the hospital bill is for Arjun Mehta."
}
```

---

## Checks

At minimum:

```text
patient identity
claim category vs documents
treatment/document dates
bill totals vs line items
prescribed diagnostic test vs diagnostic report
```

---

## Errors

```text
CONSISTENCY_CHECK_ERROR
INSUFFICIENT_DATA_FOR_CHECK
CONFLICTING_DOCUMENT_DATA
```

---

# 12. Policy Repository

## Responsibility

Load and expose the policy configuration.

The policy repository is the source of truth for policy terms.

---

## Interface

```text
get_policy(policy_id: str) -> Policy
```

---

## Input

```text
policy_id
```

---

## Output

A normalized `Policy` object containing:

```text
coverage
limits
co-pay
network discounts
waiting periods
exclusions
pre-authorization requirements
network hospitals
submission rules
document requirements
fraud thresholds
members
```

The supplied policy configuration contains these categories of information.

---

## Errors

```text
POLICY_NOT_FOUND
POLICY_LOAD_ERROR
POLICY_SCHEMA_ERROR
POLICY_VERSION_ERROR
```

---

## Invariants

The repository must return a validated policy object.

It must not silently return partial policy configuration as if it were complete.

---

# 13. Member Repository

## Responsibility

Resolve the member and retrieve member-specific information required for eligibility checks.

---

## Interface

```text
get_member(
 member_id: str,
 policy_id: str
) -> Member
```

---

## Input

```text
member_id
policy_id
```

---

## Output

```json
{
 "member_id": "EMP001",
 "name": "Rajesh Kumar",
 "date_of_birth": "1985-03-15",
 "gender": "M",
 "relationship": "SELF",
 "join_date": "2024-04-01",
 "dependents": [
 "DEP001",
 "DEP002"
 ]
}
```

---

## Errors

```text
MEMBER_NOT_FOUND
MEMBER_NOT_ACTIVE
MEMBER_POLICY_MISMATCH
MEMBER_LOAD_ERROR
```

---

# 14. Policy Evaluator

## Responsibility

Evaluate structured claim evidence against policy rules.

This component is deterministic.

---

## Interface

```text
evaluate_policy(
 claim: ClaimSubmission,
 member: Member,
 policy: Policy,
 documents: list[NormalizedDocument]
) -> PolicyEvaluation
```

---

## Input

```text
ClaimSubmission
Member
Policy
NormalizedDocument[]
```

---

## Output

```json
{
 "status": "PASSED",
 "checks": [
 {
 "rule": "MEMBER_ELIGIBILITY",
 "status": "PASSED",
 "evidence": {}
 },
 {
 "rule": "WAITING_PERIOD",
 "status": "PASSED",
 "evidence": {}
 },
 {
 "rule": "EXCLUSION",
 "status": "PASSED",
 "evidence": {}
 },
 {
 "rule": "PER_CLAIM_LIMIT",
 "status": "PASSED",
 "evidence": {
 "limit": "5000.00",
 "claimed": "1500.00"
 }
 }
 ],
 "failed_rules": [],
 "warnings": []
}
```

---

## Rule categories

```text
MEMBER_ELIGIBILITY
COVERAGE
WAITING_PERIOD
EXCLUSION
PER_CLAIM_LIMIT
ANNUAL_LIMIT
CATEGORY_SUB_LIMIT
PRE_AUTH
SUBMISSION_DEADLINE
DOCUMENT_REQUIREMENT
NETWORK_STATUS
```

---

## Errors

```text
POLICY_EVALUATION_ERROR
MISSING_POLICY_RULE
INSUFFICIENT_CLAIM_EVIDENCE
INVALID_POLICY
```

---

## Invariants

The evaluator must:

- use the supplied policy;
- not invent policy terms;
- return evidence for failed rules;
- keep rule evaluation deterministic;
- not calculate the final approved amount itself.

---

# 15. Pre-Authorization Checker

## Responsibility

Determine whether the treatment requires pre-authorization and whether valid pre-authorization evidence exists.

---

## Interface

```text
check_pre_authorization(
 claim: ClaimSubmission,
 policy: Policy,
 documents: list[NormalizedDocument]
) -> PreAuthResult
```

---

## Input

```text
ClaimSubmission
Policy
NormalizedDocument[]
```

---

## Output

```json
{
 "required": true,
 "present": false,
 "valid": false,
 "status": "FAILED",
 "reason": "MRI costing more than ₹10,000 requires pre-authorization."
}
```

---

## Errors

```text
PRE_AUTH_CHECK_ERROR
INVALID_PRE_AUTH_DATA
```

---

# 16. Financial Calculation Engine

## Responsibility

Calculate the financially eligible amount after applicable policy adjustments.

This component is fully deterministic.

---

## Interface

```text
calculate_amount(
 claimed_amount: Decimal,
 eligible_items: list[ClaimLineItem],
 policy: Policy,
 provider_context: ProviderContext
) -> FinancialCalculation
```

---

## Input

```text
claimed_amount
eligible_items
policy
provider_context
```

---

## Output

Example:

```json
{
 "currency": "INR",
 "claimed_amount": "4500.00",
 "eligible_before_adjustments": "4500.00",
 "network_discount": {
 "percent": 20,
 "amount": "900.00"
 },
 "after_network_discount": "3600.00",
 "copay": {
 "percent": 10,
 "amount": "360.00"
 },
 "approved_amount": "3240.00",
 "adjustments": [
 {
 "type": "NETWORK_DISCOUNT",
 "amount": "900.00"
 },
 {
 "type": "COPAY",
 "amount": "360.00"
 }
 ]
}
```

---

## Calculation order

The engine must apply adjustments in the defined order:

```text
Claimed Amount
 │
 ▼
Eligible Amount
 │
 ▼
Network Discount
 │
 ▼
Co-pay
 │
 ▼
Approved Amount
```

For network consultation claims:

```text
₹4,500
→ 20% discount
→ ₹3,600
→ 10% co-pay
→ ₹3,240
```

---

## Errors

```text
INVALID_AMOUNT
CALCULATION_ERROR
UNSUPPORTED_CURRENCY
INVALID_POLICY_ADJUSTMENT
```

---

## Invariants

- no floating-point arithmetic;
- no negative approved amount;
- approved amount cannot exceed eligible amount;
- every adjustment is recorded;
- calculation order is deterministic.

---

# 17. Partial Approval Engine

## Responsibility

Separate eligible and ineligible line items.

---

## Interface

```text
evaluate_line_items(
 items: list[ClaimLineItem],
 policy: Policy
) -> LineItemEvaluation
```

---

## Input

```json
[
 {
 "description": "Root Canal Treatment",
 "amount": "8000.00"
 },
 {
 "description": "Teeth Whitening",
 "amount": "4000.00"
 }
]
```

---

## Output

```json
{
 "approved_items": [
 {
 "description": "Root Canal Treatment",
 "amount": "8000.00"
 }
 ],
 "rejected_items": [
 {
 "description": "Teeth Whitening",
 "amount": "4000.00",
 "reason_code": "EXCLUDED_PROCEDURE",
 "reason": "Teeth whitening is excluded under the policy."
 }
 ],
 "approved_amount": "8000.00"
}
```

---

## Errors

```text
LINE_ITEM_PARSE_ERROR
LINE_ITEM_POLICY_MATCH_ERROR
INVALID_LINE_ITEM_AMOUNT
```

---

# 18. Fraud / Risk Analyzer

## Responsibility

Identify suspicious patterns and produce risk signals.

It does not automatically label a claim as fraudulent.

---

## Interface

```text
analyze_risk(
 claim: ClaimSubmission,
 member: Member,
 policy: Policy,
 claims_history: list[HistoricalClaim]
) -> FraudAnalysis
```

---

## Input

```text
ClaimSubmission
Member
Policy
HistoricalClaim[]
```

---

## Output

Example:

```json
{
 "risk_level": "HIGH",
 "fraud_score": 0.84,
 "signals": [
 {
 "code": "SAME_DAY_CLAIM_LIMIT_EXCEEDED",
 "severity": "HIGH",
 "evidence": {
 "existing_claim_count": 3,
 "current_claim_number_for_day": 4,
 "policy_limit": 2
 }
 }
 ],
 "recommended_action": "MANUAL_REVIEW"
}
```

---

## Signal examples

```text
SAME_DAY_CLAIM_LIMIT_EXCEEDED
MONTHLY_CLAIM_LIMIT_EXCEEDED
HIGH_VALUE_CLAIM
HIGH_FRAUD_SCORE
```

---

## Errors

```text
CLAIMS_HISTORY_UNAVAILABLE
RISK_ANALYSIS_ERROR
INVALID_HISTORY_DATA
```

---

## Invariant

A fraud signal should generally produce:

```text
MANUAL_REVIEW
```

rather than an automatic rejection unless a separate deterministic policy rule independently rejects the claim.

---

# 19. Confidence Engine

## Responsibility

Calculate the confidence of the overall processing result based on evidence quality and processing health.

---

## Interface

```text
calculate_confidence(
 document_results: list[DocumentAnalysis],
 consistency: ConsistencyResult,
 policy_result: PolicyEvaluation,
 fraud_result: FraudAnalysis,
 component_health: ComponentHealth[]
) -> ConfidenceResult
```

---

## Input

All relevant processing evidence and component-health information.

---

## Output

```json
{
 "confidence": 0.91,
 "degraded": false,
 "factors": [
 {
 "factor": "DOCUMENT_QUALITY",
 "impact": 0.0
 },
 {
 "factor": "COMPONENT_HEALTH",
 "impact": 0.0
 }
 ],
 "manual_review_recommended": false
}
```

Degraded example:

```json
{
 "confidence": 0.68,
 "degraded": true,
 "factors": [
 {
 "factor": "COMPONENT_FAILURE",
 "impact": -0.20
 }
 ],
 "manual_review_recommended": true
}
```

---

## Errors

```text
CONFIDENCE_CALCULATION_ERROR
INVALID_CONFIDENCE_FACTOR
```

---

## Invariants

```text
0.0 <= confidence <= 1.0
```

Confidence must never be used to override a deterministic rejection rule.

---

# 20. Decision Engine

## Responsibility

Convert policy results, financial calculations, risk signals and confidence into the final claim decision.

---

## Interface

```text
make_decision(
 policy_result: PolicyEvaluation,
 financial_result: FinancialCalculation,
 line_item_result: LineItemEvaluation | None,
 fraud_result: FraudAnalysis,
 confidence_result: ConfidenceResult,
 processing_health: ProcessingHealth
) -> DecisionResult
```

---

## Input

The engine consumes structured results only.

It should not call the LLM.

---

## Output

```json
{
 "decision": "APPROVED",
 "approved_amount": "1350.00",
 "currency": "INR",
 "reason_codes": [],
 "reasons": [
 "Claim is covered under the consultation benefit.",
 "Required documents were verified.",
 "10% consultation co-pay was applied."
 ],
 "confidence": 0.94,
 "manual_review_recommended": false
}
```

---

## Supported decisions

```text
APPROVED
PARTIAL
REJECTED
MANUAL_REVIEW
```

---

## Decision precedence

The engine follows explicit precedence rather than allowing components to compete arbitrarily.

Conceptually:

```text
Blocking input/document failure
 │
 ▼
 no decision

Deterministic rejection
 │
 ▼
 REJECTED

Eligible + high-risk/manual-review condition
 │
 ▼
 MANUAL_REVIEW

Some eligible + some ineligible items
 │
 ▼
 PARTIAL

Fully eligible
 │
 ▼
 APPROVED
```

---

## Errors

```text
DECISION_ENGINE_ERROR
MISSING_POLICY_RESULT
MISSING_FINANCIAL_RESULT
INVALID_DECISION_STATE
```

---

# 21. Trace / Audit Component

## Responsibility

Record enough structured information to reconstruct how a claim was processed.

---

## Interface

```text
record_event(event: TraceEvent) -> TraceEvent
```

and:

```text
get_trace(claim_id: str) -> list[TraceEvent]
```

---

## Input

```json
{
 "trace_id": "TR_0042",
 "claim_id": "CLM_0042",
 "step": "policy_evaluation",
 "component": "PolicyEvaluator",
 "status": "SUCCESS",
 "timestamp": "2024-11-01T10:15:30Z",
 "duration_ms": 82,
 "evidence": {
 "rule": "PER_CLAIM_LIMIT",
 "claimed": "1500.00",
 "limit": "5000.00",
 "result": "PASSED"
 }
}
```

---

## Output

```json
{
 "event_id": "EVT_123",
 "trace_id": "TR_0042",
 "persisted": true
}
```

---

## Errors

```text
TRACE_WRITE_ERROR
TRACE_SERIALIZATION_ERROR
TRACE_QUERY_ERROR
```

---

## Invariants

Trace events must:

- be associated with a claim;
- identify the component;
- identify success/failure/degraded state;
- contain safe evidence;
- never expose secrets;
- avoid unnecessary raw medical PII;
- preserve enough information to reconstruct the decision.

---

# 22. Persistence Repository

## Responsibility

Persist and retrieve claim-processing state.

The repository abstracts PostgreSQL/Supabase implementation from domain components.

---

## Interface

```text
save_claim(claim: Claim) -> Claim
save_document(document: DocumentRecord) -> DocumentRecord
save_extraction(extraction: ExtractionRecord) -> ExtractionRecord
save_policy_evaluation(result: PolicyEvaluation) -> PolicyEvaluation
save_decision(result: DecisionResult) -> DecisionResult
```

And:

```text
get_claim(claim_id: str) -> Claim
get_trace(claim_id: str) -> list[TraceEvent]
```

---

## Errors

```text
DATABASE_CONNECTION_ERROR
DATABASE_TIMEOUT
DATABASE_CONSTRAINT_ERROR
DATABASE_TRANSACTION_ERROR
RECORD_NOT_FOUND
```

---

## Invariants

Persistence failures must be visible to the orchestrator.

A claim should not be reported as fully persisted if a required persistence operation failed.

---

# 23. Claim History Repository

## Responsibility

Retrieve historical claims needed for risk and annual-limit checks.

---

## Interface

```text
get_claim_history(
 member_id: str,
 start_date: date | None,
 end_date: date | None
) -> list[HistoricalClaim]
```

---

## Output

```json
[
 {
 "claim_id": "CLM_0081",
 "date": "2024-10-30",
 "amount": "1200.00",
 "category": "CONSULTATION",
 "provider": "City Clinic A"
 }
]
```

---

## Errors

```text
CLAIM_HISTORY_QUERY_ERROR
DATABASE_TIMEOUT
```

---

# 24. Network Provider Resolver

## Responsibility

Determine whether the healthcare provider is in the policy's network and return applicable network benefits.

---

## Interface

```text
resolve_provider(
 provider_name: str,
 policy: Policy
) -> ProviderContext
```

---

## Output

```json
{
 "provider_name": "Apollo Hospitals",
 "network": true,
 "network_discount_percent": 20
}
```

Non-network example:

```json
{
 "provider_name": "Example Clinic",
 "network": false,
 "network_discount_percent": 0
}
```

---

## Errors

```text
PROVIDER_RESOLUTION_ERROR
AMBIGUOUS_PROVIDER
```

---

# 25. Policy Rule Contract

Every policy rule should expose the same conceptual interface.

```text
evaluate(
 claim,
 member,
 policy,
 evidence
) -> RuleResult
```

---

## RuleResult

```json
{
 "rule_code": "WAITING_PERIOD",
 "status": "FAILED",
 "severity": "BLOCKING",
 "reason": "Diabetes treatment falls within the applicable waiting period.",
 "evidence": {
 "join_date": "2024-09-01",
 "treatment_date": "2024-10-15",
 "required_days": 90
 }
}
```

---

## Status

```text
PASSED
FAILED
NOT_APPLICABLE
UNKNOWN
```

---

## Severity

```text
INFO
WARNING
BLOCKING
```

---

# 26. Component Failure Contract

Every component that can fail independently should expose failure information in a common shape.

```json
{
 "component": "DocumentAI",
 "status": "FAILED",
 "error_code": "VISION_PROVIDER_TIMEOUT",
 "message": "Document analysis timed out.",
 "retryable": true,
 "blocking": true,
 "timestamp": "2024-11-01T10:15:30Z"
}
```

---

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `component` | string | Failed component |
| `status` | enum | Failure state |
| `error_code` | string | Stable machine-readable error |
| `message` | string | Safe human-readable explanation |
| `retryable` | boolean | Whether retry may succeed |
| `blocking` | boolean | Whether safe processing can continue |

---

# 27. Processing Health Contract

The orchestrator aggregates component health.

```json
{
 "degraded": true,
 "failed_components": [
 {
 "component": "FraudAnalyzer",
 "error_code": "RISK_ANALYSIS_ERROR",
 "blocking": false
 }
 ],
 "skipped_components": [],
 "manual_review_recommended": true
}
```

---

## Purpose

This object allows the final decision to communicate:

```text
Decision = APPROVED
Confidence = 0.71
Degraded = true
Manual review recommended = true

Reason:
Fraud analysis was unavailable during processing.
```

This directly supports graceful degradation.

---

# 28. API Contract — Submit Claim

## Endpoint

```http
POST /api/claims
```

---

## Request

```text
Content-Type: multipart/form-data
```

Fields:

```text
member_id
policy_id
claim_category
treatment_date
claimed_amount
documents[]
```

---

## Response

```json
{
 "claim_id": "CLM_0042",
 "status": "PROCESSING",
 "trace_id": "TR_0042"
}
```

---

## Errors

```text
400 INVALID_REQUEST
413 FILE_TOO_LARGE
415 UNSUPPORTED_MEDIA_TYPE
422 VALIDATION_ERROR
500 INTERNAL_PROCESSING_ERROR
```

---

# 29. API Contract — Get Claim

## Endpoint

```http
GET /api/claims/{claim_id}
```

---

## Response

```json
{
 "claim_id": "CLM_0042",
 "member_id": "EMP001",
 "policy_id": "PLUM_GHI_2024",
 "claim_category": "CONSULTATION",
 "treatment_date": "2024-11-01",
 "claimed_amount": "1500.00",
 "status": "COMPLETED",
 "decision": "APPROVED",
 "approved_amount": "1350.00",
 "confidence": 0.94,
 "degraded": false
}
```

---

# 30. API Contract — Get Trace

## Endpoint

```http
GET /api/claims/{claim_id}/trace
```

---

## Response

```json
{
 "claim_id": "CLM_0042",
 "trace_id": "TR_0042",
 "events": [
 {
 "step": "input_validation",
 "status": "SUCCESS"
 },
 {
 "step": "document_verification",
 "status": "SUCCESS"
 },
 {
 "step": "policy_evaluation",
 "status": "SUCCESS"
 },
 {
 "step": "financial_calculation",
 "status": "SUCCESS"
 },
 {
 "step": "decision",
 "status": "SUCCESS"
 }
 ]
}
```

---

# 31. Error Taxonomy

Errors are divided into four broad categories.

## 31.1 Client errors

The request itself is invalid.

```text
INVALID_CLAIM
INVALID_FILE
UNSUPPORTED_FILE_TYPE
MISSING_FIELD
```

These normally return an HTTP 4xx response.

---

## 31.2 Blocking domain errors

The claim cannot safely continue.

```text
MISSING_REQUIRED_DOCUMENT
WRONG_DOCUMENT_TYPE
UNREADABLE_REQUIRED_DOCUMENT
PATIENT_MISMATCH
INVALID_POLICY
```

These should produce a structured claim-processing result rather than a generic HTTP 500.

---

## 31.3 Retryable infrastructure errors

A temporary external/system failure occurred.

```text
VISION_PROVIDER_TIMEOUT
DATABASE_TIMEOUT
TEMPORARY_PROVIDER_UNAVAILABLE
```

These may be retried according to bounded retry policy.

---

## 31.4 Non-blocking component failures

The pipeline can continue without the component.

```text
OPTIONAL_ENRICHMENT_FAILURE
NON_CRITICAL_RISK_ANALYSIS_FAILURE
OPTIONAL_EXPLANATION_FAILURE
```

These must:

```text
be recorded
→ mark processing degraded
→ reduce confidence where appropriate
→ optionally recommend manual review
```

---

# 32. Contract for Graceful Degradation

The system must never hide a component failure.

For a non-critical failure:

```text
Component failure
 │
 ▼
Record failure
 │
 ▼
Continue with available evidence
 │
 ▼
Mark degraded = true
 │
 ▼
Reduce confidence
 │
 ▼
Recommend manual review when appropriate
```

The final result should therefore be capable of representing:

```json
{
 "decision": "APPROVED",
 "approved_amount": "4000.00",
 "confidence": 0.68,
 "degraded": true,
 "manual_review_recommended": true,
 "failed_components": [
 "FraudAnalyzer"
 ]
}
```

This is important for scenarios where one component fails but a safe decision can still be produced.

---

# 33. Contract for Early Document Blocking

Early document failures have a stricter contract than generic errors.

The result must contain:

```json
{
 "status": "BLOCKED",
 "problem": {
 "uploaded_type": "PRESCRIPTION",
 "required_type": "HOSPITAL_BILL"
 },
 "action": "REUPLOAD",
 "message": "A prescription was uploaded, but a hospital bill is required for this claim."
}
```

The user-facing message must be:

- specific;
- actionable;
- document-type aware;
- safe to display to the member.

A generic message such as:

```text
Invalid documents.
```

is insufficient.

---

# 34. Contract for Decision Explainability

Every final decision must have enough structured evidence to answer:

```text
What was submitted?
What documents were found?
What documents were required?
What information was extracted?
Which checks passed?
Which checks failed?
Which policy rule caused the outcome?
How was the amount calculated?
Were there fraud/risk signals?
Did any component fail?
Why is the confidence at this level?
```

The minimum final decision structure is:

```json
{
 "decision": "PARTIAL",
 "approved_amount": "8000.00",
 "reason_codes": [
 "PARTIAL_COVERAGE"
 ],
 "reasons": [
 "Root Canal Treatment is covered.",
 "Teeth Whitening is excluded."
 ],
 "line_item_results": [],
 "confidence": 0.93,
 "degraded": false,
 "manual_review_recommended": false,
 "trace_id": "TR_0042"
}
```

---

# 35. Contract Relationships

The components form the following dependency graph:

```text
                         ┌──────────────────┐
                         │  ClaimSubmission │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Input Validator │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Document Processor│
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────────┐
                         │ Document Verification│
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Document Normalizer  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Consistency Checker  │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │Member Repository│ │Policy Repository│ │ Claim History │
        └────────┬───────┘ └───────┬────────┘ └───────┬────────┘
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Policy Evaluator   │
                         └──────────┬───────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                     ▼                             ▼
             ┌──────────────────┐         ┌──────────────────┐
             │ Provider Resolver│         │ Pre-Auth Checker │
             └────────┬─────────┘         └────────┬─────────┘
                      │                            │
                      └──────────────┬─────────────┘
                                     │
                                     ▼
                         ┌──────────────────────┐
                         │ Financial Calculator │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Fraud / Risk Analyzer│
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Confidence Engine   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Decision Engine    │
                         └──────────┬───────────┘
                                    │
                       ┌────────────┴────────────┐
                       │                         │
                       ▼                         ▼
                ┌──────────────┐          ┌──────────────┐
                │ Trace / Audit│          │ Persistence  │
                └──────┬───────┘          └──────┬───────┘
                       │                         │
                       └────────────┬────────────┘
                                    │
                                    ▼
                              Final Result
```
---

# 36. Reimplementation Guidance

An engineer reimplementing the system should be able to replace any individual component while preserving the contracts.

For example, the Document AI implementation could change:

```text
Gemini Vision
 ↓
OpenAI Vision
 ↓
Self-hosted OCR + VLM
```

without changing:

```text
DocumentVerifier
ConsistencyChecker
PolicyEvaluator
CalculationEngine
DecisionEngine
```

Similarly, PostgreSQL could be replaced by another persistence implementation as long as the repository contract remains unchanged.

The contract is therefore the stable boundary; the implementation behind it is replaceable.

---

# 37. What Components Must Remain Deterministic?

The following components should remain deterministic:

```text
Input Validator
Document Requirement Verification
Consistency Rules
Policy Repository
Policy Evaluator
Pre-Authorization Checker
Financial Calculation Engine
Partial Approval Engine
Network Provider Resolver
Decision Engine
```

AI can assist upstream interpretation, but it should not silently replace these deterministic rules.

---

# 38. What Components May Use AI?

AI is appropriate for:

```text
Document classification
OCR
Handwriting interpretation
Medical document extraction
Messy-field normalization
Semantic document understanding
Optional natural-language explanation
```

AI output must always be converted into validated structured data before entering the deterministic domain core.

---

# 39. Contract Versioning

As the system evolves, contracts should be versioned.

Example:

```text
DocumentAnalysis.v1
DocumentAnalysis.v2

PolicyEvaluation.v1
DecisionResult.v1
TraceEvent.v1
```

A version field can be included where long-lived persistence or asynchronous processing requires compatibility.

Example:

```json
{
 "schema_version": "1.0",
 "decision": "APPROVED"
}
```

This prevents a future worker from interpreting an old persisted payload using a new schema incorrectly.

---

# 40. Idempotency Contract

Any component that performs persistence or external processing should support idempotent execution where practical.

Example:

```text
claim_id = CLM_0042
processing_id = PROC_0042
component = FinancialCalculation
```

A retry of the same processing operation should not create duplicate financial records.

Conceptually:

```text
                    ┌──────────────────────────┐
                    │ (idempotency_key,        │
                    │        component)        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                       ┌──────────────────┐
                       │ Existing result? │
                       └────────┬─────────┘
                                │
                     ┌──────────┴──────────┐
                     │                     │
                    Yes                    No
                     │                     │
                     ▼                     ▼
             ┌──────────────┐      ┌──────────────┐
             │Return existing│      │    Execute   │
             │    result     │      │              │
             └──────────────┘      └──────┬───────┘
                                          │
                                          ▼
                                    ┌────────────┐
                                    │  Persist   │
                                    └────────────┘
```
---

# 41. Security Contract

Components must follow common security rules.

### Upload components

- validate MIME type;
- enforce size limits;
- reject corrupted files;
- never execute uploaded content.

### AI components

- send only required document data;
- never expose API secrets;
- sanitize provider errors;
- avoid unnecessary raw PII in prompts where possible.

### Trace components

- never store API keys;
- avoid unnecessary medical PII;
- sanitize error payloads;
- preserve audit evidence without storing unnecessary raw documents.

### Persistence components

- use parameterized queries/ORM;
- enforce access controls;
- protect credentials through environment configuration.

---

# 42. Contract Testing

Each component should have tests for:

### Happy path

```text
valid input → expected output
```

### Invalid input

```text
malformed input → typed error
```

### Boundary conditions

```text
limit exactly reached
limit exceeded
waiting period exactly elapsed
zero/negative amounts
empty documents
```

### Failure

```text
provider timeout
database failure
malformed AI response
```

### Idempotency

```text
same request twice → no duplicate side effects
```

---

# 43. Acceptance-Test Mapping

The component contracts directly support the supplied acceptance scenarios.

| Test Case | Primary Components |
|---|---|
| TC001 — Wrong Document | Document AI + Document Verification |
| TC002 — Unreadable Document | Document AI + Document Verification |
| TC003 — Different Patients | Extraction + Consistency Checker |
| TC004 — Clean Approval | Full pipeline |
| TC005 — Diabetes Waiting Period | Policy Evaluator |
| TC006 — Dental Partial Approval | Line Item Engine + Policy Evaluator |
| TC007 — MRI Pre-auth | Pre-Auth Checker + Policy Evaluator |
| TC008 — Per-Claim Limit | Policy Evaluator + Calculation Engine |
| TC009 — Same-Day Claims | Claim History + Fraud Analyzer |
| TC010 — Network Discount | Provider Resolver + Calculation Engine |
| TC011 — Component Failure | Orchestrator + Processing Health + Confidence |
| TC012 — Excluded Treatment | Policy Evaluator + Decision Engine |

The supplied test suite defines these 12 scenarios and their expected behaviors.

---

# 44. Contract Summary

| Component | Input | Output | Can Block? | AI? |
|---|---|---|---:|---:|
| Claim Orchestrator | ClaimSubmission | ClaimProcessingResult | Yes | No |
| Input Validator | ClaimSubmission | ValidationResult | Yes | No |
| Document Adapter | DocumentReference | DocumentArtifact | Yes | No |
| Document AI | DocumentArtifact | DocumentAnalysis | Yes | Yes |
| Document Classifier | DocumentAnalysis | DocumentClassification | Yes | Usually |
| Document Verifier | Claim + Documents + Policy | VerificationResult | Yes | No |
| Normalizer | DocumentAnalysis | NormalizedDocument | Yes | No |
| Consistency Checker | Claim + Documents | ConsistencyResult | Yes | No |
| Policy Repository | policy_id | Policy | Yes | No |
| Member Repository | member_id + policy_id | Member | Yes | No |
| Policy Evaluator | Claim + Member + Policy + Evidence | PolicyEvaluation | Yes | No |
| Pre-auth Checker | Claim + Policy + Evidence | PreAuthResult | Yes | No |
| Provider Resolver | Provider + Policy | ProviderContext | No | No |
| Calculation Engine | Amount + Items + Policy | FinancialCalculation | Yes | No |
| Partial Approval Engine | Line Items + Policy | LineItemEvaluation | No | No |
| Fraud Analyzer | Claim + History + Policy | FraudAnalysis | No | Optional |
| Confidence Engine | Processing Evidence | ConfidenceResult | No | No |
| Decision Engine | Policy + Financial + Risk + Confidence | DecisionResult | No | No |
| Trace/Audit | TraceEvent | Persisted Event | No | No |
| Persistence Repository | Domain Records | Persisted Records | Yes | No |
| Claim History | Member + Date Range | Historical Claims | No | No |

---

# 45. Final Contract Principle

The system is intentionally designed so that **components can be replaced without changing the business domain**.

```text
                    ┌───────────────────────────┐
                    │      Stable Contracts     │
                    └─────────────┬─────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
               ▼                  ▼                  ▼
       ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
       │  AI Provider   │ │    Database    │ │  Orchestrator  │
       │ Implementation │ │ Implementation │ │ Implementation │
       └───────┬────────┘ └───────┬────────┘ └───────┬────────┘
               │                  │                  │
               └──────────────────┼──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Same domain      │
                         │    behavior      │
                         └──────────────────┘
```

The key architectural boundary is:

> **Components exchange validated, structured domain data—not implementation-specific objects, raw LLM responses, or hidden side effects.**

This makes the system easier to test, reason about, replace and scale while preserving deterministic claim-processing behavior.