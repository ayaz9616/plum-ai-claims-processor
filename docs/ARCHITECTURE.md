# Plum Claims AI — Architecture Document

> **AI-powered Health Insurance Claims Processing System** 
> **Assignment:** Plum — AI Engineer 
> **Architecture style:** Modular Monolith · AI-assisted Pipeline · Deterministic Decision Core 
> **Primary goal:** Reliable, explainable and failure-tolerant claims automation

---

## 1. Executive Summary

Plum Claims AI automates the review of health-insurance claims submitted with medical documents such as prescriptions, hospital bills, diagnostic reports and pharmacy bills.

The central architectural decision is to **use AI where interpretation is difficult and deterministic software where correctness is non-negotiable**.

The system therefore separates:

- **AI-assisted document understanding** — classification, OCR/vision extraction, handwriting interpretation and normalization.
- **Deterministic verification and policy logic** — required-document checks, identity consistency, waiting periods, exclusions, limits and pre-authorization.
- **Deterministic financial calculation** — discounts, co-pay, sub-limits and approved amounts.
- **Risk and confidence assessment** — fraud signals, degraded processing and confidence adjustments.
- **Trace-first observability** — every important decision is reconstructable from structured events.

The current implementation intentionally uses a **modular monolith rather than microservices**. The assignment is small enough that introducing distributed infrastructure would increase operational complexity without improving the core evaluation outcome.

The code is structured around clear component boundaries so that the same domain pipeline can later be moved behind queues/workers or split into services without rewriting the business rules.

> **Important implementation note:** the current submitted system is not presented as a fully autonomous multi-agent production system. The architecture is deliberately designed with agent-like component boundaries and a future LangGraph orchestration path, but the current implementation prioritizes deterministic reliability over adding orchestration technology merely for appearance.

---

## 2. Problem and Design Goals

The assignment requires the system to:

1. Accept a claim and uploaded medical documents.
2. Detect document problems before making a claim decision.
3. Extract structured information from messy medical documents.
4. Evaluate the claim against policy terms.
5. Produce `APPROVED`, `PARTIAL`, `REJECTED`, or `MANUAL_REVIEW`.
6. Provide approved amount, reasons and confidence.
7. Make every decision explainable.
8. Continue safely when an individual component fails.

The architecture was designed around five priorities:

| Priority | Design response |
|---|---|
| **Correctness** | Deterministic policy and financial engines |
| **Explainability** | Structured trace generated at every major step |
| **AI reliability** | Provider abstraction + structured/validated outputs |
| **Resilience** | Typed failures, degraded state, confidence reduction |
| **Simplicity** | Modular monolith instead of premature microservices |

The supplied assignment explicitly makes architecture, observability, AI integration and failure handling important evaluation areas.

---

# 3. Architecture at a Glance

```text
                         ┌──────────────────────────┐
                         │      Next.js / React     │
                         │   Claim Submission UI    │
                         │   Decision Review UI     │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       FastAPI API        │
                         │ Validation + API Boundary│
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │    Claim Orchestrator    │
                         │    Pipeline / State Flow │
                         └────────────┬─────────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  │                   │                   │
                  ▼                   ▼                   ▼
        ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
        │    Document AI   │ │   Consistency /  │ │  Fraud Analysis  │
        │ Classification   │ │   Verification   │ │  & Risk Signals  │
        │ OCR + Extraction │ │   Hybrid Logic   │ │                  │
        └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                 │                    │                    │
                 ▼                    │                    │
        ┌──────────────────┐          │                    │
        │ Gemini Vision /  │          │                    │
        │   LLM Provider   │          │                    │
        └────────┬─────────┘          │                    │
                 │                    │                    │
                 └────────────────────┼────────────────────┘
                                      │
                                      ▼
              ┌─────────────────────────────────────────────┐
              │            DETERMINISTIC DOMAIN CORE        │
              │                                             │
              │ Policy Repository → Policy Evaluator        │
              │                                             │
              │ Calculation Engine                           │
              │                                             │
              │ Decision Engine                              │
              │                                             │
              │ Confidence Engine                            │
              └──────────────────────┬──────────────────────┘
                                     │
                                     ▼
                         ┌──────────────────────┐
                         │  Trace / Audit Layer │
                         │   Structured Events  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ PostgreSQL / Supabase│
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Decision + Trace UI │
                         └──────────────────────┘
```

---

# 4. Architectural Style

## 4.1 Modular Monolith

The current system is intentionally a **modular monolith**.

This means:

- one backend deployment;
- one API boundary;
- one database;
- logically separated domain components;
- explicit contracts between components;
- no unnecessary network calls between internal modules.

Conceptually:

```text
                       ┌──────────────────────┐
                       │   FastAPI Application │
                       └──────────┬───────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
                 ▼                ▼                ▼
        ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
        │    Document    │ │    Claim     │ │    Policy      │
        │     Module     │ │    Module    │ │    Module      │
        └───────┬────────┘ └──────┬───────┘ └───────┬────────┘
                │                 │                 │
                ▼                 ▼                 ▼
        ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
        │  AI Provider   │ │ Orchestrator │ │  Calculation   │
        │                │ │              │ │                │
        └────────────────┘ └──────┬───────┘ └────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Decision / Trace │
                         └──────────────────┘
```

This provides most of the architectural benefits needed for the assignment without the operational cost of microservices.

### Why not microservices?

Microservices were considered and rejected for the current scope because:

- the assignment has a relatively small domain;
- deployment time is limited;
- the system does not yet require independent horizontal scaling of every component;
- network boundaries would introduce additional failure modes;
- distributed tracing and deployment would increase complexity;
- the business logic is easier to test when the domain pipeline is local and explicit.

The important part is that **the internal boundaries are still explicit**. If scale later justifies service extraction, the contracts already exist.

---

# 5. End-to-End Claim Lifecycle

A claim moves through the following logical stages:

```text
1. Receive Claim
       │
       ▼
2. Validate Input
       │
       ▼
3. Inspect / Classify Documents
       │
       ▼
4. Verify Required Documents
       │
       ├── Missing / Wrong / Unreadable
       │          └──► BLOCKED
       │
       ▼
5. Extract Structured Information
       │
       ▼
6. Cross-Document Consistency
       │
       ├── Patient mismatch
       │          └──► BLOCKED / MANUAL REVIEW
       │
       ▼
7. Policy Evaluation
       │
       ├── Waiting period
       ├── Exclusion
       ├── Limit
       ├── Pre-auth
       └── Coverage
       │
       ▼
8. Financial Calculation
       │
       ├── Sub-limit
       ├── Network discount
       └── Co-pay
       │
       ▼
9. Fraud / Risk Analysis
       │
       ├── High-risk signal
       │          └──► MANUAL_REVIEW
       │
       ▼
10. Confidence Calculation
       │
       ▼
11. Final Decision
       │
       ├── APPROVED
       ├── PARTIAL
       ├── REJECTED
       └── MANUAL_REVIEW
       │
       ▼
12. Persist Result + Trace
```

The assignment explicitly requires early document problem detection, explainability and graceful degradation.

---

# 6. Layered Responsibilities

## Layer 1 — API / Presentation

**Technology**

- Next.js
- React
- TypeScript
- FastAPI
- Pydantic

**Responsibilities**

- collect claim inputs;
- upload documents;
- validate request shape;
- display processing status;
- display decision;
- display confidence;
- display policy checks;
- display financial breakdown;
- display fraud signals;
- display failed components;
- display trace timeline.

The UI is deliberately a **review interface**, not just a form. An operations reviewer should be able to understand why a claim was approved or rejected.

---

## Layer 2 — Orchestration

The orchestrator owns the sequence and routing of the claim pipeline.

It is responsible for:

- creating claim state;
- invoking components;
- deciding whether the pipeline can continue;
- stopping on blocking document errors;
- routing fraud/high-risk cases to manual review;
- collecting component failures;
- aggregating the final result;
- ensuring trace events are emitted.

The orchestration layer does **not** own policy calculations.

This separation prevents workflow code from becoming a large collection of business rules.

---

# 7. Document Processing Architecture

Document processing is the part of the system where AI adds the most value.

The supplied document guide specifically expects difficult inputs including handwritten prescriptions, phone photographs, skew, shadows, stamps, partially illegible text, multilingual documents, multi-page PDFs and corrected/altered documents.

## 7.1 Document Processing Flow

```text
Uploaded Image / PDF
 │
 ▼
File Validation
 │
 ▼
Document Understanding
 │
 ├── Document Type
 ├── Patient Name
 ├── Dates
 ├── Amounts
 ├── Doctor / Hospital
 ├── Diagnosis
 └── Line Items
 │
 ▼
Structured Output
 │
 ▼
Pydantic Validation
 │
 ▼
Domain Pipeline
```

## 7.2 AI Provider Boundary

AI calls are isolated behind provider abstractions.

```text
                         ┌────────────────┐
                         │ VisionProvider  │
                         └───────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
        ┌────────────────────────┐  ┌────────────────┐
        │ GeminiVisionProvider   │  │ Future Provider│
        └────────────┬───────────┘  └────────────────┘
                     │
                     ▼
                  Gemini
```

The rest of the application consumes structured domain objects rather than Gemini-specific responses.

This means a future provider change should not require rewriting:

- document verification;
- policy evaluation;
- financial calculation;
- fraud rules;
- confidence;
- decision logic;
- persistence;
- frontend behavior.

---

# 8. AI vs Deterministic Logic

This is one of the most important architectural decisions.

## AI is allowed to interpret

AI is useful for:

- document classification;
- OCR / vision extraction;
- handwriting interpretation;
- messy document understanding;
- field extraction;
- normalization;
- semantic consistency assistance;
- optional natural-language explanations.

## AI is not authoritative for money or policy

The following are deterministic:

```text
Policy limits
Waiting-period arithmetic
Exclusion execution
Pre-authorization thresholds
Sub-limits
Network discounts
Co-pay
Approved amount
Final deterministic decision
```

### Why?

An LLM can produce a plausible answer that is still numerically or logically wrong.

For example, TC010 explicitly requires:

```text
₹4,500 claimed
 │
 ▼
20% network discount
 │
 ▼
₹3,600
 │
 ▼
10% co-pay
 │
 ▼
₹360 deduction
 │
 ▼
₹3,240 approved
```

This calculation should never depend on an LLM.

The policy configuration itself is supplied as structured data and contains coverage, limits, waiting periods, exclusions, pre-authorization requirements and member information.

---

# 9. Deterministic Policy Engine

The policy engine reads policy configuration rather than scattering rules throughout application code.

Conceptually:

```text
policy_terms.json
 │
 ▼
Policy Repository
 │
 ▼
Policy Evaluator
 │
 ├── Coverage
 ├── Waiting Period
 ├── Exclusion
 ├── Sub-limit
 ├── Pre-auth
 ├── Network Status
 └── Submission Rules
 │
 ▼
Rule Results
```

## Rule output

Each rule should produce structured information such as:

```json
{
 "rule": "WAITING_PERIOD",
 "status": "FAILED",
 "evidence": {
 "condition": "DIABETES",
 "required_days": 90,
 "treatment_date": "2024-10-15"
 },
 "reason": "Diabetes waiting period has not elapsed"
}
```

The decision engine consumes these structured rule results instead of rediscovering the policy logic.

---

# 10. Financial Calculation Engine

Financial calculations are isolated from AI and policy interpretation.

## Example

```text
Claimed Amount
 │
 ▼
Eligible Amount
 │
 ▼
Category / Sub-limit
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

Money should use `Decimal` or integer minor units.

Floating-point arithmetic is deliberately avoided for claim calculations.

Every intermediate calculation becomes trace evidence:

```text
claimed_amount = ₹4,500
network_discount = 20%
discount_amount = ₹900
discounted_amount = ₹3,600
copay = 10%
copay_amount = ₹360
approved_amount = ₹3,240
```

This directly supports the assignment's requirement that an operations reviewer can understand exactly how a decision was reached.

---

# 11. Document Verification and Early Blocking

Early blocking is intentionally placed before policy adjudication.

Examples from the acceptance scenarios:

### TC001 — Wrong document

```text
Expected:
Prescription + Hospital Bill

Received:
Prescription + Prescription

Result:
BLOCKED
```

The user-facing error should say what was found and what is missing rather than returning a generic validation error.

### TC002 — Unreadable document

```text
Prescription → readable
Pharmacy Bill → unreadable

Result:
BLOCKED / REQUEST RE-UPLOAD
```

The system does not reject the claim merely because a document needs to be re-uploaded.

### TC003 — Patient mismatch

```text
Prescription → Rajesh Kumar
Hospital Bill → Arjun Mehta

Result:
BLOCKED
```

The specific names are surfaced to the user.

These cases are important because the assignment explicitly states that the quality of the user-facing message is part of the evaluation.

---

# 12. Cross-Document Consistency

After extraction, information from documents is compared.

Typical checks:

```text
Prescription patient
 vs
Hospital bill patient

Prescription date
 vs
Bill / treatment date

Prescribed test
 vs
Diagnostic report

Claim category
 vs
Document types

Bill total
 vs
Line-item total
```

A mismatch is treated as evidence, not silently ignored.

```text
Mismatch detected
 │
 ├── Blocking inconsistency
 │ └── Stop / Manual Review
 │
 └── Non-blocking inconsistency
 └── Continue + lower confidence
```

---

# 13. Fraud / Risk Analysis

Fraud analysis is deliberately separated from deterministic policy evaluation.

The goal is not to call every suspicious pattern fraud.

Instead, the system produces **signals**.

Example:

```text
Member: EMP008

Existing same-day claims:
₹1,200
₹1,800
₹2,100

Current claim:
₹4,800

Same-day count after current claim = 4
Policy threshold = 2
```

Result:

```text
MANUAL_REVIEW
```

with the specific signal included in the output.

This follows TC009, which explicitly requires manual review rather than automatic rejection.

---

# 14. Confidence Architecture

Confidence is not treated as an LLM-generated number.

It is derived from the quality of the processing path.

Conceptually:

```text
Base Confidence
 │
 ├── Document quality penalty
 ├── Extraction uncertainty penalty
 ├── Missing evidence penalty
 ├── Component failure penalty
 ├── Consistency uncertainty penalty
 └── Risk/manual-review signals
 │
 ▼
Final Confidence
```

For example:

```text
Normal full pipeline
 → high confidence

One non-critical component fails
 → lower confidence

Document partially unreadable
 → lower confidence

Blocking inconsistency
 → no automatic decision

High fraud signal
 → MANUAL_REVIEW
```

TC011 specifically requires the system to continue after a simulated component failure, expose the failure, reduce confidence and recommend manual review.

---

# 15. Graceful Degradation

A component failure should not automatically become an HTTP 500.

The system distinguishes between:

### Blocking failure

The missing information makes a safe decision impossible.

```text
Missing required document
Unreadable required document
Patient identity mismatch
Invalid claim input
```

→ stop processing.

### Non-blocking failure

The failed component is useful but not necessary for a safe partial decision.

```text
Optional enrichment
Non-critical analysis
Optional explanation generation
```

→ continue, record failure, reduce confidence.

Conceptually:

```text
Component
 │
 ├── success ──────────────► continue
 │
 ├── blocking failure ─────► stop safely
 │
 └── non-blocking failure ─► continue degraded
 │
 ├── failed_components
 ├── degraded = true
 ├── lower confidence
 └── manual review recommendation
```

---

# 16. Trace-First Observability

Observability is a first-class architectural concern.

Each significant stage emits a structured trace event containing, where applicable:

```text
trace_id
claim_id
step
component
status
duration
safe input summary
safe output summary
evidence
error
retry_count
```

Example:

```json
{
 "trace_id": "tr_123",
 "claim_id": "CLM_0042",
 "step": "financial_calculation",
 "component": "CalculationEngine",
 "status": "SUCCESS",
 "evidence": {
 "claimed_amount": 4500,
 "network_discount_percent": 20,
 "discounted_amount": 3600,
 "copay_percent": 10,
 "approved_amount": 3240
 }
}
```

## Why trace every stage?

Without a trace:

```text
APPROVED ₹3,240
```

is just an answer.

With a trace:

```text
₹4,500 claimed
→ network hospital
→ 20% discount
→ ₹3,600 eligible
→ 10% co-pay
→ ₹3,240 approved
```

it becomes an explainable decision.

The assignment explicitly assigns 20% of the evaluation to observability and requires decisions to be reconstructable from the trace.

---

# 17. Persistence Model

The structured state is persisted in PostgreSQL / Supabase PostgreSQL.

Conceptual entities:

```text
claims
 │
 ├── documents
 │ └── document_extractions
 │
 ├── policy_evaluations
 │
 ├── fraud_signals
 │
 ├── decision
 │
 └── trace_events
```

A claim should retain the policy ID/version used for evaluation so that the decision remains reproducible even if policy configuration changes later.

---

# 18. Document Storage Strategy

For the MVP, medical documents are treated as transient processing inputs.

```text
Upload
 │
 ▼
Validate
 │
 ▼
Temporary memory / file
 │
 ▼
Gemini Vision / extraction
 │
 ▼
Structured extraction
 │
 ▼
Persist structured result + trace
 │
 ▼
Delete temporary document
```

This deliberately avoids adding a permanent document-storage system to the assignment MVP.

For a production deployment, the storage interface can be replaced with S3-compatible object storage without changing the domain layer.

---

# 19. API Boundary

The intended API surface is small and domain-oriented.

```text
GET /health

POST /api/claims
POST /api/claims/{claim_id}/process

GET /api/claims
GET /api/claims/{claim_id}
GET /api/claims/{claim_id}/trace

GET /api/policies/{policy_id}
GET /api/members/{member_id}
```

The API is responsible for transport and validation.

It should not contain:

- policy calculations;
- LLM prompting logic;
- financial formulas;
- fraud rules;
- decision logic.

Those belong to domain components.

---

# 20. Contracts and Type Safety

Important boundaries use structured schemas.

Representative contracts include:

```text
ClaimSubmission
Claim
DocumentArtifact
DocumentClassification
DocumentExtraction
DocumentVerificationResult
ConsistencyResult
PolicyEvaluation
RuleResult
FinancialCalculationResult
FraudAnalysis
ConfidenceResult
DecisionResult
TraceEvent
```

Pydantic validation prevents malformed AI output from silently entering business logic.

The assignment separately requires a component-contract deliverable defining inputs, outputs and errors for significant components.

---

# 21. Current Architecture vs Future Agentic Architecture

 However, adding agents everywhere would not automatically make the system better.

## Current architecture

```text
FastAPI
 │
 ▼
Claim Orchestrator
 │
 ├── Document Processing
 ├── Verification
 ├── Consistency
 ├── Policy
 ├── Calculation
 ├── Fraud
 ├── Confidence
 └── Decision
```

This is a **modular processing pipeline** with clear AI/deterministic boundaries.

## Future orchestration layer

The component boundaries are intentionally compatible with a state-machine / LangGraph-style orchestrator:

```text
Claim State
 │
 ▼
Input Validation
 │
 ▼
Document Agent
 │
 ▼
Verification Gate
 │
 ├── blocked ──────────────► Member Action
 │
 ▼
Extraction Agent
 │
 ▼
Consistency Agent
 │
 ▼
Policy Agent / Rule Engine
 │
 ▼
Calculation Engine
 │
 ▼
Fraud / Risk Agent
 │
 ▼
Confidence
 │
 ▼
Decision
```

The important point is that **the future agent layer orchestrates existing contracts rather than replacing deterministic business logic with LLM calls**.

This is also consistent with the project's technology direction: LangGraph is intended as an orchestration/state layer, while deterministic domain services remain authoritative.

---

# 22. Why We Did Not Build Every Component as an Agent

An agentic design was considered.

It was not made the foundation because:

1. policy evaluation is deterministic;
2. financial calculation is deterministic;
3. confidence should be reproducible;
4. claim decisions need auditability;
5. unnecessary LLM calls increase latency and cost;
6. agent autonomy can make failure behavior less predictable;
7. the assignment rewards engineering judgment, not technology count.

The better boundary is:

> **Use an agent where the problem requires reasoning; use a normal function where the problem requires correctness.**

---

# 23. Technology Choices

| Area | Choice | Reason |
|---|---|---|
| Frontend | Next.js + React + TypeScript | Fast full-stack UI development |
| Backend | Python + FastAPI | Strong fit for AI/document workflows |
| Validation | Pydantic | Typed API/domain boundaries |
| AI | Google Gemini | Multimodal document understanding |
| AI abstraction | `LLMProvider` / `VisionProvider` | Provider independence |
| Database | PostgreSQL / Supabase | Structured relational claim data |
| Money | `Decimal` | Exact financial calculations |
| Testing | pytest | Unit + integration + resilience tests |
| Evaluation | Dedicated eval runner | Repeatable 12-case evaluation |
| Observability | Structured trace events | Explainability and auditability |
| Deployment | Vercel + Render + Supabase | Simple low-cost deployment model |

The technology stack and provider boundaries are documented separately in the project implementation notes.

---

# 24. Alternatives Considered and Rejected

## 24.1 Microservices

**Rejected for MVP.**

Reason:

- too much operational overhead;
- unnecessary network boundaries;
- no current need for independent scaling;
- slower iteration.

**Future use:** split document processing or asynchronous adjudication workers if load requires it.

---

## 24.2 Kubernetes

**Rejected.**

Kubernetes would solve a problem the assignment does not currently have.

At this scale:

```text
Kubernetes
+ service mesh
+ ingress
+ secrets
+ deployments
+ observability
```

would add complexity without improving claim correctness.

---

## 24.3 Redis / Kafka / RabbitMQ

**Not required for the MVP.**

They become relevant when:

- claim processing becomes asynchronous;
- workloads need buffering;
- retries need durable queues;
- workers need independent horizontal scaling.

The future architecture can introduce a queue without changing domain contracts.

---

## 24.4 Vector Database / RAG

**Not required for the current policy engine.**

The policy data is structured and rule-oriented.

A vector database would be useful if the system later needs:

- large unstructured policy documents;
- semantic policy retrieval;
- insurer-specific policy manuals;
- historical claim retrieval;
- knowledge-assisted operations.

For the current structured `policy_terms.json`, deterministic lookup is simpler and safer.

---

## 24.5 LLM-based Final Decision

**Rejected.**

The LLM can interpret documents, but the final decision must remain explainable and reproducible.

---

## 24.6 Permanent Document Storage

**Excluded from MVP.**

The assignment focuses on processing and decisioning rather than document archival.

A production object-storage abstraction can be added later.

---

# 25. Security and Privacy

Medical claims contain sensitive information.

Minimum controls include:

- validate upload type;
- restrict file size;
- sanitize filenames;
- never execute uploaded files;
- isolate temporary files;
- keep API keys in environment variables;
- never commit secrets;
- sanitize API errors;
- minimize medical PII in logs;
- avoid persisting raw AI prompts/responses unnecessarily;
- avoid storing original medical documents when not required.

Trace events should contain **evidence summaries**, not unnecessary raw medical documents.

---

# 26. Failure Model

The system uses typed failures rather than treating every error identically.

Conceptual categories:

```text
ValidationError
DocumentProcessingError
DocumentUnreadableError
MissingDocumentError
DocumentMismatchError
PolicyEvaluationError
CalculationError
ExternalProviderError
PersistenceError
```

Each failure is mapped to one of:

```text
BLOCK
CONTINUE_DEGRADED
RETRY
MANUAL_REVIEW
```

This makes resilience behavior explicit.

---

# 27. Testing Strategy

Testing is performed at multiple levels.

## Unit tests

Examples:

```text
PolicyEvaluator
CalculationEngine
ConfidenceEngine
DecisionEngine
DocumentVerifier
FraudAnalyzer
```

## Component tests

Verify contracts independently.

## Integration tests

Verify the complete pipeline:

```text
API
 ↓
Orchestrator
 ↓
Domain services
 ↓
Persistence
```

## Resilience tests

Simulate:

```text
LLM failure
Malformed AI response
Unreadable document
Missing document
Component failure
```

## Acceptance evaluation

The supplied `test_cases.json` contains 12 scenarios covering:

- wrong documents;
- unreadable documents;
- patient mismatch;
- clean approval;
- waiting periods;
- partial approval;
- missing pre-authorization;
- limits;
- fraud signals;
- network discounts;
- component failure;
- exclusions.

The evaluation runner should use the same domain pipeline rather than implementing test-specific production behavior.

---

# 28. Deterministic Evaluation Boundary

There is an important separation between production document processing and deterministic evaluation fixtures.

## Production

```text
Image / PDF
 │
 ▼
Gemini Vision / OCR
 │
 ▼
Structured Document Result
 │
 ▼
Same Domain Pipeline
```

## Evaluation

```text
test_cases.json
 │
 ▼
Test Fixture Adapter
 │
 ▼
Structured Document Result
 │
 ▼
Same Domain Pipeline
```

Fixture fields such as `actual_type` and predefined extraction content belong only to the test adapter.

They must never become shortcuts in production document classification.

---

# 29. Performance Characteristics

The current system is optimized for **correctness and explainability over maximum throughput**.

The most expensive stage is expected to be multimodal AI inference.

Approximate workload shape:

```text
HTTP request
 │
 ├── cheap deterministic validation
 │
 ├── document processing ← expensive / variable
 │
 ├── deterministic policy
 │
 ├── calculation
 │
 └── persistence
```

This makes the document-processing stage the natural candidate for asynchronous execution at higher scale.

---

# 30. What Happens at 10× Current Load?

The architecture is deliberately designed so that scaling does not require rewriting the domain layer.

## Current

```text
Client
 │
 ▼
FastAPI
 │
 ▼
In-process Pipeline
 │
 ├── Gemini
 ├── Policy
 ├── Calculation
 ├── Fraud
 └── PostgreSQL
```

## 10× target

```text
                         ┌───────────────┐
                         │ Load Balancer │
                         └───────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             ┌──────────────┐          ┌──────────────┐
             │ API Instance │          │ API Instance │
             │      1       │          │      N       │
             └───────┬──────┘          └───────┬──────┘
                     │                         │
                     └────────────┬────────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  Durable Job Queue  │
                       └──────────┬──────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ Worker 1 │  │ Worker 2 │  │ Worker N │
              └─────┬────┘  └─────┬────┘  └─────┬────┘
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
                 Gemini      PostgreSQL    Object Storage
```

### Scaling changes

#### 1. Make processing asynchronous

Instead of:

```text
POST /claim → process everything → response
```

use:

```text
POST /claim
 ↓
claim_id
 ↓
queue
 ↓
worker
 ↓
processing
```

The UI can poll or subscribe to claim status.

#### 2. Horizontal worker scaling

Document-processing workers can scale independently:

```text
10 claims
 ↓
2 workers

100 claims
 ↓
10 workers

1000 claims
 ↓
100+ workers
```

subject to provider limits and cost controls.

#### 3. Queue-based backpressure

A queue prevents sudden traffic spikes from overwhelming:

- Gemini;
- CPU;
- database connections.

#### 4. Provider rate limiting

The AI adapter should enforce:

- bounded concurrency;
- exponential backoff;
- request timeouts;
- retry limits;
- circuit-breaking where appropriate.

#### 5. Object storage

At larger scale, temporary documents should move from local memory/files to object storage.

```text
Upload
 ↓
Object Storage
 ↓
Worker
 ↓
Gemini
```

#### 6. PostgreSQL scaling

At 10× load:

- add indexes based on query patterns;
- use connection pooling;
- paginate claims;
- separate heavy trace queries;
- archive old traces;
- introduce read replicas if necessary.

#### 7. Trace storage

Trace volume can become significant.

A production version could:

```text
Hot trace data
 ↓
PostgreSQL

Older trace data
 ↓
Cold storage / analytics store
```

without changing the trace event schema.

---

# 31. 10× Scaling Bottlenecks

| Bottleneck | Current approach | 10× approach |
|---|---|---|
| AI inference | Synchronous provider call | Worker pool + queue |
| API throughput | Single/modular backend | Horizontally scaled API |
| AI rate limits | Provider abstraction | Concurrency control + backoff |
| Documents | Temporary files | Object storage |
| DB connections | Standard pool | Tuned pool + pooling layer |
| Trace volume | PostgreSQL | Partition/archive/analytics |
| Large claim lists | DB queries | Pagination + indexes |
| Retries | Local handling | Queue-aware retry/dead-letter |
| Failure recovery | In-process | Durable jobs + idempotency |

---

# 32. Idempotency at Scale

A production version should make claim processing idempotent.

For example:

```text
claim_id = CLM_123
processing_attempt = 4
```

If a worker crashes after Gemini succeeds but before persistence, retrying should not create duplicate decisions or duplicate financial records.

The system should therefore use:

```text
claim_id
+
pipeline_version
+
processing_attempt
```

and transactional persistence.

---

# 33. Cost Control at Scale

AI inference is likely to dominate variable processing cost.

Potential optimizations:

1. validate file metadata before AI;
2. block missing documents early;
3. avoid duplicate document processing;
4. cache deterministic extraction where safe;
5. resize extremely large images;
6. route simple documents to cheaper models;
7. reserve stronger models for low-confidence cases;
8. avoid sending unnecessary document pages;
9. use asynchronous batching where provider capabilities permit.

The guiding principle is:

> **Do not spend an expensive AI call when a cheap deterministic check can answer the question.**

---

# 34. Architecture Trade-offs

## Trade-off 1 — Simplicity vs distribution

**Chosen:** modular monolith.

**Benefit:** faster development, simpler debugging, fewer failure modes.

**Cost:** less independent scaling.

**Future:** extract workers/services when load justifies it.

---

## Trade-off 2 — AI flexibility vs deterministic correctness

**Chosen:** AI for interpretation, code for policy and money.

**Benefit:** predictable financial decisions.

**Cost:** more explicit engineering effort.

**Future:** use AI to assist rule discovery/explanation, but keep executable rules deterministic.

---

## Trade-off 3 — Full document archival vs transient processing

**Chosen:** transient MVP documents.

**Benefit:** lower storage/privacy complexity.

**Cost:** harder historical document reprocessing.

**Future:** object storage + retention policies if required.

---

## Trade-off 4 — Agentic architecture vs controlled pipeline

**Chosen:** controlled modular pipeline.

**Benefit:** predictable behavior and easier evaluation.

**Cost:** less autonomous orchestration.

**Future:** introduce LangGraph/stateful agent orchestration around existing contracts.

---

# 35. Limitations of the Current Design

The current system is intentionally an assignment-scale implementation, not a complete insurance production platform.

### 1. AI extraction is probabilistic

Messy handwriting, stamps and low-quality photos can still cause extraction errors.

### 2. Real-world document coverage is incomplete

The supplied guide contains many variations, including handwritten and multilingual documents. The current test fixtures do not represent the full diversity of real medical documents.

### 3. AI provider dependency

Gemini availability, latency and rate limits affect processing.

### 4. Synchronous processing

The current deployment is suitable for assignment-scale traffic but should become queue-backed for significantly higher throughput.

### 5. Limited fraud intelligence

The current fraud layer focuses on explicit signals such as claim frequency and thresholds rather than sophisticated graph-based fraud detection.

### 6. No full human-review workflow

The system can recommend manual review, but a production platform would need:

- reviewer assignment;
- queues;
- reviewer actions;
- escalation;
- SLA tracking;
- audit history.

### 7. Policy versioning can be expanded

A production system should support immutable policy snapshots and effective-date based policy resolution.

---

# 36. Future Production Architecture

A mature version could evolve toward the following architecture:

```text
                         ┌──────────────────────┐
                         │   Web / Operations   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  API Gateway / Auth  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Claim Service     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Durable Job Queue  │
                         └──────────┬───────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │ Document       │ │ Policy         │ │ Fraud          │
        │ Workers        │ │ Workers        │ │ Workers        │
        └───────┬────────┘ └───────┬────────┘ └───────┬────────┘
                │                  │                  │
                ▼                  │                  │
        ┌────────────────┐         │                  │
        │ Vision /       │         │                  │
        │ LLM APIs       │         │                  │
        └───────┬────────┘         │                  │
                │                  │                  │
                └──────────────────┼──────────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │ Decision Orchestrator  │
                       └────────────┬───────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
          │  PostgreSQL  │  │ Object Store │  │  Trace Store │
          └───────┬──────┘  └──────────────┘  └──────────────┘
                  │
                  ▼
          ┌────────────────┐
          │  Review Queue  │
          └────────────────┘
```

This evolution keeps the **domain contracts stable** while allowing the infrastructure to scale independently around them.

---

# 37. Design Principles

The implementation follows these principles:

### 1. Determinism where money is involved

Never delegate arithmetic to an LLM.

### 2. AI as an interpreter, not an authority

AI converts messy real-world inputs into structured evidence.

### 3. Fail visibly

A hidden failure is worse than an explicit degraded result.

### 4. Stop early when the evidence is invalid

Do not perform expensive adjudication if required documents are wrong or unreadable.

### 5. Every decision should be explainable

A reviewer should be able to reconstruct the decision without reading application code.

### 6. Contracts over implementation details

Components communicate through typed domain structures.

### 7. Scale the expensive boundary independently

At higher load, document/AI processing should become asynchronous and horizontally scalable.

### 8. Do not add infrastructure without a reason

Architecture complexity should solve an actual problem.

---

# 38. Final Architecture Decision

The final architecture is intentionally **boring in the places where boring is good and intelligent in the places where intelligence adds value**.

```text
                         ┌───────────────┐
                         │      USER     │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ Next.js / React│
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │    FastAPI    │
                         └───────┬───────┘
                                 │
                                 ▼
                      ┌─────────────────────┐
                      │ Claim Orchestrator  │
                      └──────────┬──────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  │              │              │
                  ▼              ▼              ▼
           ┌────────────┐ ┌────────────┐ ┌──────────────┐
           │ Document AI│ │Consistency │ │Fraud Signals │
           └─────┬──────┘ └─────┬──────┘ └──────┬───────┘
                 │              │               │
                 ▼              │               │
           ┌────────────┐       │               │
           │   Gemini   │       │               │
           └─────┬──────┘       │               │
                 │              │               │
                 └──────────────┼───────────────┘
                                │
                                ▼
                     ┌────────────────────┐
                     │ Deterministic Core │
                     └──────────┬─────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
          ┌──────────┐    ┌────────────┐   ┌──────────┐
          │  Policy  │    │ Calculation│   │ Decision │
          │  Engine  │    │   Engine   │   │  Engine  │
          └────┬─────┘    └─────┬──────┘   └────┬─────┘
               │                │               │
               └────────────────┼───────────────┘
                                │
                                ▼
                         ┌────────────┐
                         │ Confidence │
                         └─────┬──────┘
                               │
                               ▼
                         ┌────────────┐
                         │Trace/Audit │
                         └─────┬──────┘
                               │
                               ▼
                         ┌────────────┐
                         │ PostgreSQL │
                         └─────┬──────┘
                               │
                               ▼
                       ┌────────────────┐
                       │ Review / Result│
                       └────────────────┘
```

The architecture intentionally optimizes for the evaluation criteria:

- **System Design:** clean component boundaries and a scale path;
- **Engineering Quality:** typed contracts, deterministic business logic and testable modules;
- **Observability:** trace-first decision reconstruction;
- **AI Integration:** multimodal AI behind provider boundaries;
- **Document Verification:** early, specific and actionable blocking;
- **Resilience:** graceful degradation instead of opaque failures.

The assignment's acceptance scenarios specifically test these properties across wrong documents, unreadable documents, patient mismatches, policy rules, financial calculations, fraud signals and component failure.

---

## 39. Architecture Summary for Reviewers

| Question | Answer |
|---|---|
| **Why AI?** | Medical documents are messy and require visual/semantic interpretation. |
| **Why not AI for everything?** | Policy and financial decisions must be deterministic and auditable. |
| **Why modular monolith?** | Best complexity/performance trade-off for the assignment scale. |
| **How is failure handled?** | Typed failures, blocking vs non-blocking classification, degraded state and confidence reduction. |
| **How is the decision explained?** | Structured trace events contain evidence and intermediate results. |
| **How is money calculated?** | Deterministically using exact arithmetic. |
| **How are wrong documents handled?** | Early verification gate with specific actionable messages. |
| **How does it scale?** | Queue + worker pool + horizontal API scaling + object storage + PostgreSQL scaling. |
| **Why not microservices now?** | Distributed infrastructure is unnecessary at current scale. |
| **Why not make everything an agent?** | Agents add uncertainty where deterministic functions are safer. |
| **Can Gemini be replaced?** | Yes, through the provider abstraction. |
| **Can the monolith become distributed?** | Yes, because domain contracts are separated from infrastructure. |

---

## 40. References

This architecture is based on the assignment requirements, policy configuration, test scenarios, document-format guidance and project implementation decisions.

- Plum AI Engineer Assignment — system requirements and evaluation criteria.
- Policy configuration — coverage, limits, waiting periods, exclusions and members.
- Test cases — 12 acceptance scenarios and expected behavior.
- Sample Documents Guide — expected Indian medical-document variations.
- Project technology architecture — provider abstraction, deterministic core, trace model and scaling direction.

---

> **Architecture principle:** 
> **Use AI to understand the evidence. Use deterministic software to enforce the policy. Use traces to explain the decision. Use queues and workers to scale it.**
