# Plum Claims AI — Master Engineering Plan

## 1. Purpose

This is the persistent implementation specification for GitHub Copilot and human contributors.

Source-of-truth hierarchy:
1. Official Plum `assignment.md`
2. Supplied `test_cases.json`
3. Supplied `policy_terms.json`
4. Supplied `sample_documents_guide.md`
5. Supplied `README.md`
6. `DECISIONS.md`
7. `ASSUMPTIONS.md`

Do not silently replace or "correct" supplied assignment behavior.

## 2. Mission

Build an AI-powered health-insurance claims processing system that accepts:
- member ID
- policy ID
- treatment category
- treatment date
- claimed amount
- one or more images/PDFs

and produces one of:
- `APPROVED`
- `PARTIAL`
- `REJECTED`
- `MANUAL_REVIEW`

Every completed decision must expose:
- approved amount, if applicable
- reasons
- confidence
- document evidence
- policy checks
- financial calculation
- fraud signals
- failed/degraded components
- full trace

TC001–TC003 are early document failures and must stop before claim adjudication.

## 3. Evaluation priorities

The assignment weights:
- System Design: 30%
- Engineering Quality: 25%
- Observability: 20%
- AI Integration: 15%
- Document Verification: 10%

Multi-agent architecture is a bonus.

Optimize for correctness, judgment, explainability, resilience, and testability rather than unnecessary infrastructure.

## 4. Core architectural rules

1. Document verification happens first.
2. Policy values come from configuration; do not scatter hardcoded values.
3. LLMs interpret messy/unstructured evidence; deterministic code makes policy and money decisions.
4. Every significant component has a typed contract.
5. Every significant component has tests.
6. Every claim has an auditable trace.
7. Non-critical failures degrade safely.
8. Blocking failures stop processing or route to manual review.
9. `MANUAL_REVIEW` is a valid business outcome.
10. Partial approval is line-item based.
11. Use `Decimal` or integer minor units for money.
12. Never special-case test-case IDs.
13. Never allow the LLM to invent financial amounts or final policy decisions.
14. Never expose raw stack traces or sensitive medical data to users.
15. Document policy/test interpretation discrepancies.

## 5. Recommended technology

Frontend:
- Next.js
- TypeScript
- React
- Tailwind CSS

Backend:
- Python
- FastAPI
- Pydantic
- async I/O where useful

Persistence:
- PostgreSQL for structured data
- local storage for development; object storage for deployment if needed

AI:
- provider abstraction (`LLMProvider` / vision provider)
- structured output
- timeout
- bounded retry

Use a modular monolith. Do not build distributed microservices for this assignment.

## 6. High-level architecture

```text
Next.js UI
    |
FastAPI API
    |
Claim Orchestrator
    |
    +--> Input Validation
    +--> Document Classification
    +--> Document Verification
    |       |
    |       +--> blocking -> stop
    |
    +--> Parallel Document Extraction
    +--> Cross-Document Consistency
    |       |
    |       +--> clear mismatch -> stop
    |
    +--> Policy Evaluation
    +--> Deterministic Financial Calculation
    +--> Fraud Signal Analysis
    +--> Confidence Engine
    +--> Decision Engine
    +--> Explanation Builder
    +--> Trace/Audit Store
    |
Decision Review UI
```

## 7. Processing state machine

```text
RECEIVED
 -> VALIDATING_INPUT
 -> DOCUMENT_CLASSIFICATION
 -> DOCUMENT_VERIFICATION
 -> DOCUMENT_EXTRACTION
 -> CROSS_DOCUMENT_CONSISTENCY
 -> POLICY_EVALUATION
 -> FINANCIAL_CALCULATION
 -> FRAUD_ANALYSIS
 -> CONFIDENCE_EVALUATION
 -> DECISION
 -> COMPLETED
```

Early failures:
```text
DOCUMENT_VERIFICATION -> BLOCKED_DOCUMENT
CROSS_DOCUMENT_CONSISTENCY -> BLOCKED_DOCUMENT
```

Processing status and business decision are separate.

Example:
```text
processing_status = PROCESSING_DEGRADED
decision = APPROVED
```

## 8. Critical vs non-critical

The assignment does not prescribe a critical/non-critical list. This is an architectural decision.

Blocking/critical examples:
- malformed core input
- unavailable/invalid policy context
- missing required document
- wrong required document
- unusable required evidence
- clear patient identity mismatch

Potentially degradable:
- optional field extraction
- fraud analysis
- secondary enrichment
- optional normalization
- non-essential agent timeout

A non-critical failure must be visible:
```json
{
  "degraded": true,
  "failed_components": [
    {
      "component": "fraud_agent",
      "severity": "NON_CRITICAL",
      "reason": "timeout"
    }
  ]
}
```

## 9. Policy configuration

The application must load `policy_terms.json`.

Current supplied policy includes:
- policy `PLUM_GHI_2024`
- insurer `ICICI Lombard General Insurance`
- policy period `2024-04-01` to `2025-03-31`
- sum insured ₹5,00,000
- annual OPD limit ₹50,000
- per-claim limit ₹5,000
- family floater ₹1,50,000
- category rules
- waiting periods
- exclusions
- pre-auth
- network hospitals
- fraud thresholds
- members
- document requirements

Do not duplicate these as scattered constants.

## 10. Category rules

CONSULTATION:
- sub-limit ₹2,000
- copay 10%
- network discount 20%
- prescription required
- covered

DIAGNOSTIC:
- sub-limit ₹10,000
- copay 0%
- network discount 10%
- prescription required
- pre-auth threshold ₹10,000
- MRI/CT/PET special handling
- covered

PHARMACY:
- sub-limit ₹15,000
- copay 0%
- branded drug copay 30%
- generic mandatory
- prescription required
- covered

DENTAL:
- sub-limit ₹10,000
- copay 0%
- dental report required
- covered: root canal, extraction, filling, scaling/polishing, dental X-ray, crown, gum treatment
- excluded: whitening, veneers, braces, cosmetic implants, bleaching

VISION:
- covered: glasses, contact lenses, eye examination, cataract surgery
- excluded: LASIK, cosmetic eye surgery, refractive surgery

ALTERNATIVE_MEDICINE:
- sub-limit ₹8,000
- copay 0%
- prescription required
- registered practitioner required
- max 20 sessions/year
- covered: Ayurveda, Homeopathy, Unani, Siddha, Naturopathy

## 11. Waiting periods

Load dynamically:
- initial: 30 days
- pre-existing: 365 days
- diabetes: 90 days
- hypertension: 90 days
- thyroid: 90 days
- joint replacement: 730 days
- maternity: 270 days
- mental health: 180 days
- obesity treatment: 365 days
- hernia: 365 days
- cataract: 365 days

Every waiting-period result must include evidence and eligibility date.

## 12. Document requirements

CONSULTATION:
required `PRESCRIPTION`, `HOSPITAL_BILL`
optional `LAB_REPORT`, `DIAGNOSTIC_REPORT`

DIAGNOSTIC:
required `PRESCRIPTION`, `LAB_REPORT`, `HOSPITAL_BILL`
optional `DISCHARGE_SUMMARY`

PHARMACY:
required `PRESCRIPTION`, `PHARMACY_BILL`

DENTAL:
required `HOSPITAL_BILL`
optional `PRESCRIPTION`, `DENTAL_REPORT`

VISION:
required `PRESCRIPTION`, `HOSPITAL_BILL`

ALTERNATIVE_MEDICINE:
required `PRESCRIPTION`, `HOSPITAL_BILL`

Always load this from policy.

## 13. Document types

Support:
- `PRESCRIPTION`
- `HOSPITAL_BILL`
- `LAB_REPORT`
- `PHARMACY_BILL`
- `DENTAL_REPORT`
- `DISCHARGE_SUMMARY`
- `UNKNOWN`

Never trust filenames alone.

Classification output must include:
- document ID
- detected type
- confidence
- quality
- signals

## 14. Document quality

Handle:
- handwriting
- partially illegible text
- pre-printed forms
- missing registration numbers
- medical shorthand
- mixed regional languages/English
- multiple pages
- stamps over text
- skewed phone photos
- low contrast/shadows
- partial/cut-off documents
- corrections
- duplicate stamps
- scanned PDFs

Use field-level confidence. A missing optional field should not invalidate the whole document.

## 15. Extraction

Prescription:
- doctor
- registration
- specialization
- patient
- age/gender
- date
- diagnosis
- medicines/dosage/duration
- tests
- clinic/hospital/address

Hospital bill:
- hospital/address/GSTIN
- bill number/date
- patient/age/gender
- referring doctor
- line items
- subtotal/GST/total/payment mode

Lab:
- lab/NABL
- patient/age/gender
- referring doctor
- sample/report dates
- sample ID
- tests/result/unit/reference range
- remarks
- pathologist/registration

Pharmacy bill:
- pharmacy/drug license
- bill number/date
- patient/doctor
- medicine/batch/expiry/quantity/MRP/amount
- discount/subtotal/net

Registration number patterns should be configurable, including KA/MH/DL/TN/GJ/AP/UP/WB/KL and AYUR forms from the supplied guide.

## 16. Cross-document consistency

Check:
- patient identity
- dates
- provider/doctor where relevant
- line-item sum vs total
- claim amount vs document totals
- diagnosis/treatment/test consistency

Normalize reasonable variants:
`Rajesh Kumar`, `Rajesh K.`, `R. Kumar`

Do not accept clearly different people.

Uncertain identity should prefer manual review.

## 17. Deterministic policy engine

Implement reusable evaluators:
- policy period
- member eligibility
- category coverage
- waiting period
- exclusions
- pre-authorization
- claim limit
- annual limit
- category limit
- document requirements

Each returns structured evidence.

## 18. Exclusions

Current policy includes:
- self-inflicted injuries
- war/nuclear hazard
- substance abuse treatment
- experimental treatments
- infertility/assisted reproduction
- obesity/weight-loss programs
- bariatric surgery
- cosmetic/aesthetic procedures
- non-medically necessary vaccination
- supplements/tonics

Evaluate against structured diagnosis/treatment/line-item evidence.

## 19. Pre-authorization

Required by policy for:
- MRI > ₹10,000
- CT > ₹10,000
- PET
- major surgery
- planned hospitalization

Validity: 30 days.

TC007 must produce:
`REJECTED`, `PRE_AUTH_MISSING`

## 20. Line-item adjudication

Required for TC006.

Each relevant line item gets:
- coverage status
- amount
- reason code
- explanation/evidence

Mixed results produce `PARTIAL`.

## 21. Financial calculation

Pure deterministic component.

Use Decimal.

Required order for TC010:
```text
₹4,500
 -> 20% network discount = ₹900
 -> ₹3,600
 -> 10% copay = ₹360
 -> ₹3,240 approved
```

Expose every intermediate step in the trace.

## 22. Policy/test discrepancy

The supplied policy and explicit acceptance expectations require careful interpretation in some places, especially around limits/sub-limits and TC006/TC010.

Do not:
- alter source policy silently;
- special-case TC IDs;
- hide the discrepancy.

Instead:
1. preserve policy source;
2. implement generic rule precedence;
3. document interpretation;
4. preserve evaluated rules in trace;
5. validate against acceptance outcomes.

## 23. Fraud

Current policy thresholds:
- same-day claims limit 2
- monthly claims limit 6
- high-value threshold ₹25,000
- auto-manual-review above ₹25,000
- fraud score manual-review threshold 0.80

Signals may include:
- excessive same-day claims
- excessive monthly claims
- high value
- document alteration
- duplicate stamps
- multiple providers

Fraud signal is not automatically fraud/rejection.

TC009:
4th same-day claim -> `MANUAL_REVIEW`

## 24. Failure injection / TC011

Support deterministic:
`simulate_component_failure = true`

Use an explicit failure injector.

When triggered:
- record component failure;
- continue if safe;
- mark degraded;
- lower confidence;
- recommend manual review;
- still produce expected `APPROVED` for TC011.

Never return 500 merely because the simulated component fails.

## 25. Confidence

Calculate from observable factors:
- document quality
- extraction confidence
- consistency
- policy completeness
- component health
- rule certainty
- fraud-analysis availability

Confidence must include explainable factors.

## 26. Decision precedence

Recommended:
1. blocking document/data problem -> no business decision
2. insufficient policy/context -> `MANUAL_REVIEW`
3. strong manual-review fraud/anomaly -> `MANUAL_REVIEW`
4. hard policy rejection -> `REJECTED`
5. mixed line-item outcomes -> `PARTIAL`
6. all applicable coverage passes -> `APPROVED`

Document this behavior.

## 27. Final result shape

```json
{
  "claim_id": "CLM-123",
  "decision": "APPROVED",
  "approved_amount": "3240.00",
  "confidence_score": 0.94,
  "processing_status": "COMPLETED",
  "degraded": false,
  "summary": "...",
  "reasons": [],
  "financial_breakdown": {},
  "policy_checks": [],
  "document_checks": [],
  "fraud_signals": [],
  "failed_components": [],
  "trace": []
}
```

Blocked document cases keep `decision = null`.

## 28. Trace

Every component emits:
- trace ID
- claim ID
- step
- component
- status
- duration
- safe input summary
- safe output summary
- evidence
- error
- retry count

Trace is first-class data and must be visible in the UI.

## 29. API

Recommended:
- `POST /api/claims`
- `POST /api/claims/{id}/process`
- `GET /api/claims`
- `GET /api/claims/{id}`
- `GET /api/claims/{id}/trace`
- `GET /api/policies/{id}`
- `GET /api/members/{id}`
- `GET /health`

## 30. Frontend

Claim submission:
- member
- policy
- category
- treatment date
- amount
- provider
- documents
- optional failure simulation

Decision review:
- decision
- amount
- confidence
- degraded state
- reasons
- document checks
- policy checks
- line-item decisions
- financial breakdown
- fraud signals
- trace

## 31. Database

Recommended:
`claims`, `documents`, `document_extractions`, `policy_evaluations`, `fraud_signals`, `trace_events`

Record policy ID/version used for each claim.

## 32. Security

- validate file MIME/type and size
- sanitize filenames
- safe storage
- never execute uploads
- minimize PII in logs
- never commit secrets
- sanitized API errors

## 33. Testing

Unit:
- policy
- document requirements
- waiting periods
- exclusions
- pre-auth
- limits
- calculations
- line items
- confidence
- decision precedence
- identity

Integration:
- orchestrator

E2E:
all TC001–TC012.

## 34. Evaluation runner

Create `scripts/run_evals.py`.

It must:
1. load supplied test cases;
2. execute them;
3. capture decision;
4. capture amount;
5. capture confidence;
6. capture full trace;
7. compare expected behavior;
8. write machine-readable results;
9. update human-readable report.

Never mutate expected test data.

## 35. Implementation order

Phase 0: read all sources
Phase 1: foundation
Phase 2: policy
Phase 3: documents + TC001–TC003
Phase 4: calculation + TC004/TC010
Phase 5: fraud + TC009
Phase 6: graceful failure + TC011
Phase 7: decisions + TC005–TC012
Phase 8: trace
Phase 9: frontend
Phase 10: evaluation
Phase 11: documentation
Phase 12: deployment/demo

## 36. Definition of done

Done means:
- core flow works;
- all 12 tests run;
- expected behavior passes or discrepancies are documented;
- trace reconstructs decisions;
- policy is configuration-driven;
- financial calculations are deterministic;
- structured AI outputs are validated;
- failure simulation works;
- confidence degradation is visible;
- document errors are actionable;
- contracts/docs exist;
- deployment works;
- no secrets are committed.

## 37. Copilot behavior

Before changing significant code:
1. inspect existing repository;
2. read PLAN/DECISIONS;
3. inspect relevant contracts/tests;
4. make the smallest coherent change;
5. run tests;
6. update documentation if architecture changes.

Never rewrite unrelated code.
Never claim tests pass without running them.
