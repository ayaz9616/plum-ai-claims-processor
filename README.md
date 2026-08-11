# Plum Claims AI — Architecture Document

> **AI-powered Health Insurance Claims Processing System**  
> **Assignment:** Plum — AI Engineer  
> **Architecture style:** Multi-Agent Claims Pipeline · Workflow-Orchestrated Modular Monolith · Deterministic Decision Core  
> **Primary goal:** Reliable, explainable and failure-tolerant claims automation

---

## 1. Executive Summary

Plum Claims AI automates the review of health-insurance claims submitted with medical documents such as prescriptions, hospital bills, diagnostic reports and pharmacy bills.

The system is designed as a **multi-agent claims-processing pipeline coordinated by a central workflow orchestrator**.

Specialized agents handle responsibilities where interpretation, document understanding or risk reasoning is useful:

- **Document Agent** — identifies and verifies submitted document types.
- **Extraction Agent** — extracts structured information from medical documents.
- **Consistency Agent** — checks consistency across documents and extracted evidence.
- **Fraud Agent** — evaluates fraud and risk signals.

These agents operate within a controlled workflow rather than independently making arbitrary decisions.

The output of the agent layer feeds into a **deterministic domain core** responsible for:

- policy evaluation;
- coverage rules;
- waiting periods;
- exclusions;
- pre-authorization;
- claim limits;
- financial calculations;
- confidence calculation;
- final decisioning.

The central architectural principle is:

> **Use agents and AI where interpretation is difficult. Use deterministic software where correctness is non-negotiable.**

The system is intentionally implemented as a **modular monolith** for the current assignment scope. The agent boundaries, workflow boundaries and domain contracts are explicit, allowing the expensive processing stages to be moved behind queues/workers or separated into services later without rewriting the core business logic.

The architecture also follows a **trace-first observability model**. Every significant stage produces structured trace information so that an operations user can reconstruct how the system arrived at its final decision.

---

# 2. Problem and Design Goals

The assignment requires the system to:

1. Accept a claim and uploaded medical documents.
2. Detect document problems before making a claim decision.
3. Extract structured information from messy medical documents.
4. Evaluate the claim against policy terms.
5. Produce `APPROVED`, `PARTIAL`, `REJECTED`, or `MANUAL_REVIEW`.
6. Provide approved amount, reasons and confidence.
7. Make every decision explainable.
8. Continue safely when an individual component fails.
9. Handle realistic medical document variations.
10. Demonstrate reliable AI integration rather than using an LLM as an uncontrolled decision-maker.

The architecture was designed around five priorities:

| Priority | Design response |
|---|---|
| **Correctness** | Deterministic policy and financial engines |
| **AI reliability** | Specialized agents + provider abstraction + structured validation |
| **Explainability** | Structured trace generated at every major stage |
| **Resilience** | Typed failures, degraded state and confidence reduction |
| **Simplicity** | Modular monolith with explicit agent/domain boundaries |

---

# 3. Architecture at a Glance

The system can be viewed as four major layers:

```text
                         ┌──────────────────────────────┐
                         │       Next.js / React        │
                         │     Operations / Claim UI    │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │          FastAPI API         │
                         │   Validation + API Boundary  │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                 ╔════════════════════════════════════════════╗
                 ║          WORKFLOW ORCHESTRATOR             ║
                 ║       Claim State + Agent Routing          ║
                 ╚════════════════════╤═══════════════════════╝
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
       ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
       │   DOCUMENT   │       │  EXTRACTION  │       │ CONSISTENCY  │
       │    AGENT     │       │    AGENT     │       │    AGENT     │
       │              │       │              │       │              │
       │ Classification│      │ OCR / Vision │       │ Cross-doc    │
       │ Verification │       │ Structured   │       │ validation   │
       └──────┬───────┘       │ extraction   │       └──────┬───────┘
              │               └──────┬───────┘              │
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ DETERMINISTIC     │
                           │ DOMAIN CORE       │
                           │                   │
                           │ Policy Evaluator  │
                           │ Calculation Engine│
                           │ Confidence Engine │
                           │ Decision Engine   │
                           └─────────┬─────────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │  FRAUD AGENT │
                              │              │
                              │ Risk Signals │
                              │ Pattern Check│
                              └──────┬───────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ Decision / Review │
                           └─────────┬─────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ Trace / Audit     │
                           │ Structured Events │
                           └─────────┬─────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │ PostgreSQL /      │
                           │ Supabase          │
                           └───────────────────┘
```

### Architectural layers

```text
┌───────────────────────────────────────────────┐
│                 Presentation                  │
│              Next.js / React                 │
├───────────────────────────────────────────────┤
│                     API                       │
│                   FastAPI                     │
├───────────────────────────────────────────────┤
│               Orchestration                  │
│             Workflow / State                 │
├───────────────────────────────────────────────┤
│               Agent Layer                    │
│ Document · Extraction · Consistency · Fraud  │
├───────────────────────────────────────────────┤
│            Deterministic Domain              │
│ Policy · Calculation · Confidence · Decision │
├───────────────────────────────────────────────┤
│             Infrastructure                   │
│ AI Provider · PostgreSQL · Storage            │
└───────────────────────────────────────────────┘
```

---

# 4. Multi-Agent Architecture

## 4.1 Agent Responsibilities

The agent layer contains specialized components with focused responsibilities.

```text
                         WORKFLOW
                       ORCHESTRATOR
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
     ┌───────────┐    ┌───────────┐    ┌────────────┐
     │ DOCUMENT  │    │ EXTRACTION│    │CONSISTENCY │
     │   AGENT   │    │   AGENT   │    │   AGENT    │
     └─────┬─────┘    └─────┬─────┘    └──────┬─────┘
           │                │                 │
           └────────────────┼─────────────────┘
                            │
                            ▼
                     DETERMINISTIC
                     DOMAIN CORE
                            │
                            ▼
                     ┌────────────┐
                     │ FRAUD AGENT│
                     └─────┬──────┘
                           │
                           ▼
                       DECISION
```

### Document Agent

Responsibilities:

- identify submitted document types;
- determine whether required documents are present;
- detect wrong document types;
- detect unreadable documents;
- provide actionable document-validation results;
- prevent invalid claims from entering expensive downstream processing.

Example:

```text
CONSULTATION

Required:
✓ PRESCRIPTION
✓ HOSPITAL_BILL

Received:
✓ PRESCRIPTION
✗ PRESCRIPTION (expected HOSPITAL_BILL)

Result:
BLOCKED
```

The early document gate is deliberately before extraction, policy evaluation and financial calculation.

### Extraction Agent

Responsibilities:

- process medical images/PDFs;
- use multimodal AI for document understanding;
- extract patient details;
- extract doctor details;
- extract dates;
- extract diagnosis/treatment;
- extract billing information and line items;
- normalize the result into structured domain objects.

The agent does not decide claim eligibility.

### Consistency Agent

Responsibilities:

- compare patient identity across documents;
- compare treatment dates;
- compare bill totals and line items;
- compare prescribed tests with diagnostic reports;
- identify contradictions or missing evidence;
- return structured consistency findings.

Example:

```text
Prescription:
Patient = Rajesh Kumar

Hospital Bill:
Patient = Arjun Mehta

Result:
DOCUMENT_MISMATCH
→ BLOCK / MANUAL REVIEW
```

### Fraud Agent

Responsibilities:

- evaluate risk signals;
- identify unusual claim patterns;
- detect frequency-based anomalies;
- identify high-value claims;
- surface signals rather than automatically declaring fraud.

Example:

```text
Same-day claims:
₹1,200
₹1,800
₹2,100
Current claim:
₹4,800

Same-day count = 4
Policy threshold = 2

Result:
MANUAL_REVIEW
Signal:
UNUSUAL_SAME_DAY_CLAIM_PATTERN
```

---

# 5. Workflow Orchestrator

The agents are coordinated by a central workflow/orchestration layer.

The orchestrator owns:

- claim state;
- stage ordering;
- agent invocation;
- continuation/blocking decisions;
- failure routing;
- confidence propagation;
- final aggregation;
- trace emission.

Conceptually:

```text
                       Claim State
                            │
                            ▼
                    ┌───────────────┐
                    │  Orchestrator │
                    └───────┬───────┘
                            │
                            ▼
                    Document Agent
                            │
                       verification
                       ┌────┴────┐
                       │         │
                    BLOCKED    PASS
                       │         │
                       ▼         ▼
                  Member      Extraction
                   Action        Agent
                                  │
                                  ▼
                            Consistency
                               Agent
                                  │
                                  ▼
                           Policy Engine
                                  │
                                  ▼
                           Calculation
                               Engine
                                  │
                                  ▼
                            Fraud Agent
                                  │
                                  ▼
                           Confidence
                                  │
                                  ▼
                           Decision Engine
                                  │
                                  ▼
                             Trace Store
```

The orchestrator does not own policy calculations or financial formulas. It owns **workflow and routing**.

This separation prevents orchestration code from becoming a large collection of business rules.

---

# 6. Modular Monolith

Although the system uses a multi-agent processing model, the current implementation is intentionally a **modular monolith**.

This means:

- one backend deployment;
- one API boundary;
- one database;
- logically separated agents/modules;
- explicit contracts;
- no unnecessary network calls between internal components.

Conceptually:

```text
                    ┌──────────────────────┐
                    │   FastAPI Application│
                    └──────────┬───────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
                 ▼             ▼             ▼
          ┌────────────┐ ┌────────────┐ ┌────────────┐
          │   Agents   │ │  Workflow  │ │ Deterministic│
          │   Module   │ │   Module   │ │ Core Module │
          └─────┬──────┘ └──────┬─────┘ └──────┬─────┘
                │               │               │
                └───────────────┼───────────────┘
                                ▼
                         ┌──────────────┐
                         │Infrastructure│
                         └──────────────┘
```

### Why not microservices?

Microservices were considered and rejected for the current scope because:

- the assignment has a relatively small domain;
- deployment time is limited;
- the system does not yet require independent horizontal scaling of every component;
- network boundaries would introduce additional failure modes;
- distributed tracing would add complexity;
- the business logic is easier to test when the domain pipeline is explicit.

The important part is that the internal boundaries already exist.

At higher scale, the agent and worker boundaries can be extracted without redesigning the domain contracts.

---

# 7. End-to-End Claim Lifecycle

A claim moves through the following logical stages:

```text
1. Receive Claim
       │
       ▼
2. Validate Input
       │
       ▼
3. Document Agent
       │
       ▼
4. Required Document Gate
       │
       ├── Missing / Wrong / Unreadable
       │          └──► BLOCKED
       │
       ▼
5. Extraction Agent
       │
       ▼
6. Consistency Agent
       │
       ├── Blocking mismatch
       │          └──► BLOCKED / MANUAL_REVIEW
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
9. Fraud Agent
       │
       ├── High-risk signal
       │          └──► MANUAL_REVIEW
       │
       ▼
10. Confidence Calculation
       │
       ▼
11. Decision Engine
       │
       ├── APPROVED
       ├── PARTIAL
       ├── REJECTED
       └── MANUAL_REVIEW
       │
       ▼
12. Persist Result + Trace
```

---

# 8. AI vs Deterministic Logic

This is one of the most important architectural decisions.

## AI / Agents are used for interpretation

AI is useful for:

- document classification;
- OCR / vision extraction;
- handwriting interpretation;
- messy document understanding;
- field extraction;
- normalization;
- semantic consistency assistance;
- fraud/risk interpretation;
- optional natural-language explanations.

## Deterministic software is authoritative for policy and money

The following remain deterministic:

```text
Policy limits
Waiting-period arithmetic
Exclusion execution
Pre-authorization thresholds
Sub-limits
Network discounts
Co-pay
Approved amount
Decision rules
Confidence adjustments
```

The principle is:

> **Agents handle ambiguity. Deterministic components handle business truth.**

For example, TC010 requires:

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
₹3,240 approved
```

This calculation should never depend on an LLM.

---

# 9. AI Provider Boundary

AI calls are isolated behind provider abstractions.

```text
                         ┌──────────────────┐
                         │  VisionProvider  │
                         │ / LLM Provider   │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
          ┌───────────────────┐       ┌─────────────────┐
          │ Gemini Provider   │       │ Future Provider │
          └─────────┬─────────┘       └─────────────────┘
                    │
                    ▼
                 Gemini
```

The rest of the application consumes structured domain objects rather than provider-specific responses.

A provider change should not require rewriting:

- document verification;
- policy evaluation;
- financial calculation;
- fraud rules;
- confidence;
- decision logic;
- persistence;
- frontend behavior.

---

# 10. Document Processing Architecture

Document processing is where AI adds the most value.

The supplied document guide expects difficult inputs including:

- handwritten prescriptions;
- phone photographs;
- skew and shadows;
- rubber stamps;
- partially illegible text;
- multilingual documents;
- multi-page PDFs;
- corrected or altered documents.

## Document flow

```text
Uploaded Image / PDF
        │
        ▼
File Validation
        │
        ▼
Document Agent
        │
        ├── Document Type
        ├── Quality
        └── Required Document Check
        │
        ▼
Extraction Agent
        │
        ├── Patient
        ├── Doctor
        ├── Dates
        ├── Diagnosis
        ├── Treatment
        ├── Amounts
        └── Line Items
        │
        ▼
Structured Output
        │
        ▼
Pydantic / Schema Validation
        │
        ▼
Domain Pipeline
```

---

# 11. Deterministic Policy Engine

The policy engine reads policy configuration rather than scattering rules throughout application code.

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
Structured Rule Results
```

Example:

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

The decision engine consumes structured rule results rather than rediscovering policy logic.

---

# 12. Financial Calculation Engine

Financial calculations are isolated from AI and policy interpretation.

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

---

# 13. Document Verification and Early Blocking

Early blocking is intentionally placed before expensive adjudication.

### TC001 — Wrong document

```text
Required:
PRESCRIPTION + HOSPITAL_BILL

Received:
PRESCRIPTION + PRESCRIPTION

Result:
BLOCKED
```

The user-facing error identifies both the uploaded and required document types.

### TC002 — Unreadable document

```text
Prescription → readable
Pharmacy Bill → unreadable

Result:
REQUEST RE-UPLOAD / BLOCK
```

The claim is not rejected outright merely because a required document needs to be re-uploaded.

### TC003 — Patient mismatch

```text
Prescription → Rajesh Kumar
Hospital Bill → Arjun Mehta

Result:
BLOCKED
```

The specific names are surfaced to the user.

---

# 14. Cross-Document Consistency

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
        │        └── Stop / Manual Review
        │
        └── Non-blocking inconsistency
                 └── Continue + lower confidence
```

---

# 15. Fraud / Risk Agent

Fraud analysis is separated from deterministic policy evaluation.

The goal is not to call every suspicious pattern fraud.

The Fraud Agent produces **risk signals**.

Example:

```text
Member: EMP008

Existing same-day claims:
₹1,200
₹1,800
₹2,100

Current claim:
₹4,800

Same-day count = 4
Policy threshold = 2

Result:
MANUAL_REVIEW

Signal:
UNUSUAL_SAME_DAY_CLAIM_PATTERN
```

This follows TC009, which requires manual review rather than automatic rejection.

---

# 16. Confidence Architecture

Confidence is not treated as an arbitrary LLM-generated number.

It is derived from the quality of the processing path.

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

Examples:

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

---

# 17. Graceful Degradation

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

→ stop processing safely.

### Non-blocking failure

The failed component is useful but not necessary for a safe decision.

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
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
           SUCCESS       BLOCKING       NON-BLOCKING
              │           FAILURE          FAILURE
              │              │              │
              ▼              ▼              ▼
          Continue         Stop        Continue degraded
                                           │
                                  ┌────────┼────────┐
                                  ▼        ▼        ▼
                              Record    Lower    Recommend
                              Failure  Confidence Review
```

TC011 explicitly exercises this behavior.

---

# 18. Trace-First Observability

Observability is a first-class architectural concern.

Each significant stage emits a structured trace event containing, where applicable:

```text
trace_id
claim_id
step
component / agent
status
duration
safe input summary
safe output summary
evidence
error
retry_count
confidence impact
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

---

# 19. Persistence Model

The structured state is persisted in PostgreSQL / Supabase PostgreSQL.

Conceptual entities:

```text
claims
 │
 ├── documents
 │    └── document_extractions
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

# 20. Document Storage Strategy

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
AI document processing
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

For a production deployment, this can be replaced with an object-storage abstraction such as S3-compatible storage without changing the domain layer.

---

# 21. API Boundary

The intended API surface is small and domain-oriented.

```text
GET  /health

POST /api/claims
POST /api/claims/{claim_id}/process

GET  /api/claims
GET  /api/claims/{claim_id}
GET  /api/claims/{claim_id}/trace

GET  /api/policies/{policy_id}
GET  /api/members/{member_id}
```

The API is responsible for transport and validation.

It should not contain:

- policy calculations;
- LLM prompting logic;
- financial formulas;
- fraud rules;
- decision logic.

Those belong to the appropriate agent/domain components.

---

# 22. Contracts and Type Safety

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

The component contracts make the agent/domain boundaries precise enough that individual components can be replaced or reimplemented without changing the rest of the system.

---

# 23. Current Multi-Agent Architecture vs Future Agentic Architecture

The current implementation already separates agent responsibilities:

```text
FastAPI
   │
   ▼
Workflow Orchestrator
   │
   ├── Document Agent
   ├── Extraction Agent
   ├── Consistency Agent
   └── Fraud Agent
   │
   ▼
Deterministic Domain Core
   │
   ├── Policy Evaluator
   ├── Calculation Engine
   ├── Confidence Engine
   └── Decision Engine
```

The important distinction is that these are **bounded agents coordinated by a controlled workflow**, not autonomous agents that independently choose arbitrary next actions.

This is deliberate.

### Future stateful agent orchestration

The same boundaries can later be coordinated by a state-machine or LangGraph-style workflow:

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
    ├──────────────► BLOCKED → Member Action
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
Fraud Agent
    │
    ▼
Confidence Engine
    │
    ▼
Decision Engine
```

The future orchestration layer should orchestrate existing contracts rather than replacing deterministic business logic with LLM calls.

---

# 24. Why Not Make Everything an Agent?

An agentic design was intentionally bounded.

Policy evaluation and financial calculation are deterministic problems.

Making them LLM agents would introduce:

- unnecessary uncertainty;
- harder testing;
- harder reproducibility;
- higher latency;
- higher cost;
- more complicated failure behavior.

The design principle is:

> **Use an agent where interpretation or reasoning adds value; use a normal deterministic component where correctness is the requirement.**

This also makes the architecture easier to audit.

---

# 25. Technology Choices

| Area | Choice | Reason |
|---|---|---|
| Frontend | Next.js + React + TypeScript | Full-stack UI development |
| Backend | Python + FastAPI | Strong fit for AI/document workflows |
| Validation | Pydantic | Typed API/domain boundaries |
| AI | Multimodal Gemini | Medical document understanding |
| AI abstraction | Provider interface | Provider independence |
| Database | PostgreSQL / Supabase | Structured relational claim data |
| Money | `Decimal` | Exact financial calculations |
| Testing | pytest | Unit + integration + resilience tests |
| Evaluation | Dedicated eval runner | Repeatable 12-case evaluation |
| Observability | Structured trace events | Explainability and auditability |
| Deployment | Vercel + Render + Supabase | Simple assignment-scale deployment |

---

# 26. Alternatives Considered and Rejected

## 26.1 Microservices

**Rejected for MVP.**

Reasons:

- unnecessary operational overhead;
- network boundaries introduce additional failure modes;
- no current need for independent scaling;
- distributed tracing would increase complexity;
- slower iteration for assignment scope.

**Future:** extract expensive agents/workers when scale justifies it.

---

## 26.2 Kubernetes

**Rejected.**

Kubernetes solves operational problems the current system does not yet have.

At assignment scale it would add:

- deployment complexity;
- service discovery;
- ingress;
- secrets management;
- monitoring;
- operational overhead.

---

## 26.3 Redis / Kafka / RabbitMQ

**Not required for MVP.**

They become relevant when:

- processing becomes asynchronous;
- workloads require buffering;
- retries need durable queues;
- workers require independent horizontal scaling.

---

## 26.4 Vector Database / RAG

**Not required for the current policy engine.**

The supplied policy data is structured and rule-oriented.

A vector database becomes useful if the system later needs:

- large unstructured policy documents;
- semantic policy retrieval;
- insurer-specific policy manuals;
- historical claim retrieval;
- knowledge-assisted operations.

For structured policy terms, deterministic lookup is simpler and safer.

---

## 26.5 LLM-Based Final Decision

**Rejected.**

The LLM can interpret documents, but the final business decision must remain reproducible and auditable.

---

## 26.6 Permanent Document Storage

**Excluded from MVP.**

The assignment focuses on processing and decisioning rather than document archival.

A production object-storage abstraction can be added later.

---

# 27. Security and Privacy

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

# 28. Failure Model

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

# 29. Testing Strategy

Testing is performed at multiple levels.

## Unit tests

Examples:

```text
PolicyEvaluator
CalculationEngine
ConfidenceEngine
DecisionEngine
DocumentAgent
ExtractionAgent
ConsistencyAgent
FraudAgent
DocumentVerifier
```

## Component tests

Verify contracts independently.

## Integration tests

Verify the complete pipeline:

```text
API
 ↓
Workflow
 ↓
Agents
 ↓
Deterministic Domain Core
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

---

# 30. Deterministic Evaluation Boundary

There is a separation between production document processing and deterministic evaluation fixtures.

## Production

```text
Image / PDF
 │
 ▼
Document Agent
 │
 ▼
AI / Vision Provider
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

Fixture fields such as `actual_type` and predefined extraction content belong to the test adapter.

They should never become shortcuts in production document classification.

---

# 31. Performance Characteristics

The current system is optimized for **correctness and explainability over maximum throughput**.

The most expensive stage is expected to be multimodal AI inference.

```text
HTTP request
 │
 ├── cheap deterministic validation
 │
 ├── document / AI processing ← expensive / variable
 │
 ├── deterministic policy
 │
 ├── calculation
 │
 └── persistence
```

This makes the AI/document-processing boundary the natural candidate for asynchronous execution at higher scale.

---

# 32. What Happens at 10× Current Load?

The architecture is deliberately designed so that scaling does not require rewriting the domain layer.

## Current

```text
Client
 │
 ▼
FastAPI
 │
 ▼
Workflow Orchestrator
 │
 ├── Document Agent
 ├── Extraction Agent
 ├── Consistency Agent
 ├── Policy
 ├── Calculation
 └── Fraud Agent
 │
 ▼
PostgreSQL
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
              │ Agent    │  │ Agent    │  │ Agent    │
              │ Worker 1 │  │ Worker 2 │  │ Worker N │
              └─────┬────┘  └─────┬────┘  └─────┬────┘
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
                 AI APIs      PostgreSQL    Object Storage
```

### Scaling changes

#### 1. Asynchronous processing

```text
POST /claim
    ↓
claim_id
    ↓
queue
    ↓
workers
    ↓
processing
```

The UI can poll or subscribe to claim status.

#### 2. Horizontal worker scaling

The expensive document/AI workers can scale independently.

#### 3. Queue-based backpressure

A queue prevents traffic spikes from overwhelming:

- AI provider limits;
- CPU;
- database connections.

#### 4. Provider rate limiting

The AI adapter should enforce:

- bounded concurrency;
- timeouts;
- exponential backoff;
- retry limits;
- circuit-breaking where appropriate.

#### 5. Object storage

At larger scale:

```text
Upload
 ↓
Object Storage
 ↓
Agent Worker
 ↓
AI Provider
```

#### 6. PostgreSQL scaling

At 10× load:

- add indexes based on query patterns;
- use connection pooling;
- paginate claim lists;
- separate heavy trace queries;
- archive old traces;
- add read replicas if necessary.

#### 7. Trace storage

Trace volume can become significant.

A production version could move older trace data into a lower-cost analytics/cold-storage layer while keeping the same event schema.

---

# 33. 10× Scaling Bottlenecks

| Bottleneck | Current approach | 10× approach |
|---|---|---|
| AI inference | Synchronous provider call | Worker pool + queue |
| API throughput | Single backend | Horizontally scaled API |
| AI rate limits | Provider abstraction | Concurrency control + backoff |
| Documents | Temporary files | Object storage |
| DB connections | Standard pool | Tuned pool + pooling layer |
| Trace volume | PostgreSQL | Partition/archive/analytics |
| Large claim lists | DB queries | Pagination + indexes |
| Retries | Local handling | Durable queue + dead-letter |
| Failure recovery | In-process | Durable jobs + idempotency |

---

# 34. Idempotency at Scale

A production version should make claim processing idempotent.

For example:

```text
claim_id = CLM_123
processing_attempt = 4
```

If a worker crashes after AI processing succeeds but before persistence, retrying should not create duplicate decisions or financial records.

The system should use stable identifiers and transactional persistence so that retries are safe.

---

# 35. Cost Control at Scale

AI inference is likely to dominate variable processing cost.

Potential optimizations:

1. validate file metadata before AI;
2. block missing documents early;
3. avoid duplicate document processing;
4. cache deterministic extraction where safe;
5. resize unnecessarily large images;
6. route simple documents to cheaper models;
7. reserve stronger models for low-confidence cases;
8. avoid sending unnecessary document pages;
9. use asynchronous batching where provider capabilities permit.

The guiding principle is:

> **Do not spend an expensive AI call when a cheap deterministic check can answer the question.**

---

# 36. Architecture Trade-offs

## Trade-off 1 — Multi-agent specialization vs complexity

**Chosen:** bounded specialized agents coordinated by a workflow.

**Benefit:** clear responsibilities and replaceable components.

**Cost:** more orchestration and contracts than a single AI call.

**Future:** introduce richer stateful agent orchestration only where dynamic planning provides value.

---

## Trade-off 2 — Monolith vs distributed services

**Chosen:** modular monolith.

**Benefit:** simpler deployment, debugging and testing.

**Cost:** less independent scaling.

**Future:** extract AI-heavy workers/services when required.

---

## Trade-off 3 — AI flexibility vs deterministic correctness

**Chosen:** AI for interpretation, deterministic code for policy and money.

**Benefit:** predictable financial decisions.

**Cost:** more explicit engineering effort.

**Future:** AI can assist with explanation or policy discovery while executable policy remains deterministic.

---

## Trade-off 4 — Full document archival vs transient processing

**Chosen:** transient MVP documents.

**Benefit:** lower storage/privacy complexity.

**Cost:** harder historical document reprocessing.

**Future:** object storage + retention policies.

---

# 37. Current Limitations

The current system is an assignment-scale implementation rather than a complete insurance production platform.

### 1. AI extraction is probabilistic

Messy handwriting, stamps and low-quality images can still cause extraction errors.

### 2. Real-world document diversity is larger

The supplied guide includes many variations that would require a broader production dataset and evaluation suite.

### 3. AI provider dependency

Provider availability, latency and rate limits affect processing.

### 4. Synchronous processing

The current deployment is appropriate for assignment-scale traffic but should become queue-backed for significantly higher throughput.

### 5. Limited fraud intelligence

The current Fraud Agent focuses on explicit signals such as frequency and thresholds rather than sophisticated graph-based fraud detection.

### 6. Limited human-review workflow

The system can recommend manual review, but a production platform would need:

- reviewer assignment;
- review queues;
- reviewer actions;
- escalation;
- SLA tracking;
- audit history.

### 7. Policy versioning can be expanded

A production system should support immutable policy snapshots and effective-date based policy resolution.

---

# 38. Future Production Architecture

A mature version could evolve toward:

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
        │ Document       │ │ Policy /       │ │ Fraud          │
        │ Agent Workers  │ │ Decision       │ │ Agent Workers  │
        └───────┬────────┘ │ Workers        │ └───────┬────────┘
                │          └───────┬────────┘         │
                ▼                   │                  │
        ┌────────────────┐          │                  │
        │ Vision /       │          │                  │
        │ LLM APIs       │          │                  │
        └───────┬────────┘          │                  │
                │                   │                  │
                └───────────────────┼──────────────────┘
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

This evolution preserves the domain contracts while allowing the infrastructure and expensive agents to scale independently.

---

# 39. Design Principles

### 1. Determinism where money is involved

Never delegate arithmetic to an LLM.

### 2. Agents where interpretation adds value

Use specialized agents for document understanding, extraction, consistency and risk reasoning.

### 3. AI as an interpreter, not the final authority

AI converts messy real-world inputs into structured evidence.

### 4. Fail visibly

A hidden failure is worse than an explicit degraded result.

### 5. Stop early when evidence is invalid

Do not perform expensive adjudication if required documents are wrong or unreadable.

### 6. Every decision should be explainable

A reviewer should be able to reconstruct the decision without reading application code.

### 7. Contracts over implementation details

Agents and domain components communicate through typed structures.

### 8. Scale the expensive boundary independently

At higher load, document/AI processing should become asynchronous and horizontally scalable.

### 9. Do not add infrastructure without a reason

Architecture complexity should solve an actual problem.

---

# 40. Final Architecture Decision

The final architecture intentionally combines:

```text
              MULTI-AGENT LAYER
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Document      Extraction    Consistency
      Agent         Agent          Agent
       │             │             │
       └─────────────┼─────────────┘
                     ▼
          DETERMINISTIC DOMAIN CORE
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
      Policy     Calculation    Decision
                     │
                     ▼
                Fraud Agent
                     │
                     ▼
                Confidence
                     │
                     ▼
              Explainable Trace
```

The system is intentionally **intelligent at the interpretation boundary and deterministic at the business-correctness boundary**.

The core architectural principle is:

> **Use specialized agents to understand the evidence. Use deterministic software to enforce the policy. Use structured traces to explain the decision. Use queues and workers to scale the expensive parts.**

---

# 41. Architecture Summary for Reviewers

| Question | Answer |
|---|---|
| **Is it multi-agent?** | Yes — specialized bounded agents for document, extraction, consistency and fraud responsibilities are coordinated by a workflow orchestrator. |
| **Are the agents autonomous?** | No. They operate within a controlled workflow; autonomy is deliberately bounded. |
| **Why agents?** | Different claim-processing tasks require different forms of interpretation and reasoning. |
| **Why not make everything an agent?** | Policy enforcement and financial calculations require deterministic, reproducible behavior. |
| **Why modular monolith?** | Best complexity/performance trade-off for the current assignment scope. |
| **How is failure handled?** | Typed failures, blocking vs non-blocking classification, degraded state and confidence reduction. |
| **How is the decision explained?** | Structured trace events contain evidence and intermediate results. |
| **How is money calculated?** | Deterministically using exact arithmetic. |
| **How are wrong documents handled?** | Document Agent + early verification gate with specific actionable messages. |
| **How does it scale?** | Durable queue + horizontally scalable workers + object storage + PostgreSQL scaling. |
| **Why not Kubernetes now?** | Operational complexity is unnecessary at current scale. |
| **Why not RAG?** | Current policy data is structured and rule-oriented; vector retrieval is unnecessary. |
| **Can the AI provider be replaced?** | Yes, through the provider abstraction. |
| **Can the monolith become distributed?** | Yes, because agent/domain contracts are separated from infrastructure. |

---

# 42. Architecture Principle

> **Use agents to understand messy medical evidence. Use deterministic software to enforce the policy and calculate money. Use workflows to coordinate the agents. Use traces to explain every decision. Use queues and workers to scale it when the workload demands it.**
