# Plum Claims AI — Technology Stack

## 1. Purpose

This document describes the technologies used by the Plum Claims AI system, the responsibility of each technology, the architectural boundaries between them, and the reasons behind the major implementation choices.

It complements:

- `assignment.md`
- `policy_terms.json`
- `test_cases.json`
- `sample_documents_guide.md`
- `README.md`
- `PLAN.md`
- `DECISIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/COMPONENT_CONTRACTS.md`

The assignment requirements and policy/test fixtures remain authoritative. This document describes the implementation choices made around those requirements.

---

## 2. Stack Overview

| Area | Technology | Status / Responsibility |
|---|---|---|
| Frontend | Next.js + React + TypeScript | Current demo UI |
| Styling | Tailwind CSS | UI styling |
| Backend API | Python + FastAPI | Current backend |
| Validation | Pydantic | Typed API and domain contracts |
| Orchestration | Modular claim orchestrator | **Current implementation** |
| LLM | Google Gemini | Selected AI provider |
| Vision / OCR | Google Gemini multimodal vision | Document understanding |
| AI abstraction | `LLMProvider` / `VisionProvider` | Provider-independent boundaries |
| Policy engine | Python deterministic rules | Policy enforcement |
| Calculation | Python `Decimal` | Exact financial arithmetic |
| Database | Supabase PostgreSQL | Structured application data |
| Document storage | Memory / temporary files | Transient document processing |
| Permanent document storage | None in MVP | Deliberately excluded |
| Testing | pytest | Unit, component and integration coverage |
| Acceptance evaluation | 12 acceptance scenarios | Verified separately from pytest |
| Observability | Structured trace / audit events | Explainability and debugging |
| Containerization | Docker | Reproducible deployment option |
| Frontend deployment | Vercel | Target |
| Backend deployment | Render | Target |
| Database hosting | Supabase | Target |

> **Important:** LangGraph is a planned future orchestration layer. It is **not** represented as a current runtime dependency of the MVP.

---

# 3. Backend

## 3.1 Python

Python is used for the backend because the claim-processing pipeline combines:

- AI / multimodal processing
- structured document extraction
- deterministic policy evaluation
- financial calculation
- fraud/risk analysis
- confidence calculation
- API implementation
- automated testing

The domain logic is intentionally kept independent from the web framework where practical.

---

## 3.2 FastAPI

FastAPI exposes the application API and coordinates requests with the claim-processing domain layer.

Representative API surface:

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

The exact routes may evolve with the implementation, but the API should remain a thin boundary around the domain services rather than containing policy logic itself.

---

# 4. Data Validation

Pydantic is used for important API and domain contracts.

Representative models include:

```text
ClaimSubmission
ClaimDocumentArtifact
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

The important rule is:

```text
External / AI output
        │
        ▼
Pydantic validation
        │
        ▼
Normalized domain object
        │
        ▼
Business logic
```

Invalid structured AI output must not silently enter the deterministic business layer.

---

# 5. AI / LLM — Google Gemini

## 5.1 Selected Provider

The implementation uses **Google Gemini** as the primary AI provider.

Gemini is used for tasks where interpretation of unstructured information is required, including:

- multimodal document understanding
- document classification
- OCR-assisted extraction
- handwritten text interpretation
- messy medical-document understanding
- field extraction
- normalization
- semantic consistency analysis where appropriate
- optional explanation generation

The exact Gemini model is configuration-driven rather than hardcoded throughout the application.

Example configuration:

```text
GEMINI_API_KEY=
GEMINI_MODEL=
GEMINI_OCR_MODEL=
GEMINI_TEMPERATURE=0.0
```

Credentials must never be committed to Git.

---

# 6. Gemini Vision / OCR

Google Gemini multimodal vision is used for document image and PDF understanding.

The document-processing layer must be able to deal with difficult medical-document inputs such as:

- handwritten prescriptions
- phone-camera photographs
- low-quality images
- skewed images
- shadows
- stamps
- partially illegible text
- regional or multilingual documents
- multi-page PDFs
- altered or corrected documents

The vision layer is therefore designed around **structured extraction and typed outputs**, rather than unconstrained free-form text.

## 6.1 Conceptual Flow

```text
Image / PDF
     │
     ▼
Gemini Multimodal Vision
     │
     ▼
OCR + Document Understanding
     │
     ▼
Structured Extraction
     │
     ▼
Pydantic Validation
     │
     ▼
Domain Pipeline
```

## 6.2 Expected Structured Information

Gemini should return structured information such as:

```text
document_type
document_quality
patient_name
doctor_name
dates
diagnosis
treatment
line_items
amounts
registration_numbers
confidence_per_field
evidence
signals
```

The AI output is evidence for the domain system.

It is **not** the authoritative source of financial approval.

For example:

```text
Gemini
  → extracts claimed amount = ₹4,500

Deterministic calculation engine
  → applies network discount
  → applies co-pay
  → calculates approved amount

Decision engine
  → produces final decision
```

This separation makes financial behavior reproducible and testable.

---

# 7. AI Provider Abstraction

Although Gemini is the selected implementation provider, the application should not be tightly coupled to Gemini-specific response formats.

Use provider abstractions such as:

```text
LLMProvider
VisionProvider
```

Conceptually:

```text
             LLMProvider
                  │
                  ▼
          GeminiLLMProvider
                  │
                  ▼
             Google Gemini
```

and:

```text
            VisionProvider
                  │
                  ▼
        GeminiVisionProvider
                  │
                  ▼
          Gemini Multimodal
```

The rest of the application should consume provider-neutral structured domain objects.

This allows a future provider replacement without rewriting:

- document verification
- policy evaluation
- calculation
- fraud logic
- confidence logic
- decision logic
- persistence
- UI

Possible future implementations could include other multimodal/LLM providers, but those are alternatives rather than current dependencies.

---

# 8. AI Responsibilities vs Deterministic Responsibilities

This boundary is one of the most important architectural decisions.

## 8.1 AI / Gemini Responsibilities

Gemini may handle:

```text
Document classification
OCR / vision extraction
Handwriting interpretation
Messy document understanding
Medical-document field extraction
Normalization
Semantic consistency analysis
Optional explanation generation
```

## 8.2 Deterministic Responsibilities

AI must not be the authoritative source for:

```text
Arithmetic
Claim amount calculation
Policy limits
Waiting-period arithmetic
Exclusion rule execution
Pre-authorization thresholds
Sub-limit calculations
Co-pay calculations
Network discount calculations
Final approved amount
Final deterministic policy decision
```

Those responsibilities remain application logic.

The resulting architecture is:

```text
Unstructured / Probabilistic
             │
             ▼
        Gemini Vision
             │
             ▼
     Structured Evidence
             │
             ▼
    Pydantic Validation
             │
             ▼
   Deterministic Domain Core
             │
      ┌──────┼──────┐
      ▼      ▼      ▼
    Policy  Money  Risk
      │      │      │
      └──────┼──────┘
             │
             ▼
          Decision
```

---

# 9. Current Orchestration

## 9.1 Current Implementation

The current MVP uses a **modular claim orchestrator**.

The orchestrator coordinates domain components in a predictable sequence:

```text
Claim Submission
       │
       ▼
Input Validation
       │
       ▼
Document Processing
       │
       ▼
Document Verification
       │
       ▼
Document Normalization
       │
       ▼
Cross-Document Consistency
       │
       ▼
Policy Evaluation
       │
       ▼
Financial Calculation
       │
       ▼
Fraud / Risk Analysis
       │
       ▼
Confidence
       │
       ▼
Decision
       │
       ▼
Trace / Persistence
```

The important architectural point is that the orchestrator coordinates components; it does not become the owner of every business rule.

---

# 10. Future Workflow Evolution — LangGraph

## 10.1 Status

**Planned future orchestration layer.**

LangGraph is not required to replace the deterministic domain services.

The current system already has explicit component boundaries. A future LangGraph implementation can make workflow state and conditional routing more explicit without changing those domain contracts.

Potential responsibilities:

- claim state
- node execution
- conditional routing
- failure handling
- degraded processing
- manual-review paths
- final result aggregation

## 10.2 Future Workflow

```text
Claim State
     │
     ▼
Input Validation
     │
     ▼
Document Classification
     │
     ▼
Document Verification
     │
     ├──────── blocking ────────► Blocked
     │
     ▼
Document Extraction
     │
     ▼
Cross-Document Consistency
     │
     ├──────── mismatch ───────► Blocked / Manual Review
     │
     ▼
Policy Evaluation
     │
     ▼
Financial Calculation
     │
     ▼
Fraud Analysis
     │
     ├──────── high risk ───────► Manual Review
     │
     ▼
Confidence
     │
     ▼
Decision
     │
     ▼
Trace / Result
```

Not every future workflow node needs an LLM.

| Node | AI? |
|---|---|
| Input validation | No |
| Document classification | Gemini |
| Document verification | Deterministic |
| Document extraction | Gemini |
| Consistency | Hybrid |
| Policy evaluation | Deterministic |
| Financial calculation | Deterministic |
| Fraud analysis | Hybrid |
| Confidence | Deterministic |
| Decision | Deterministic |
| Explanation | Optional Gemini |
| Trace | Deterministic |

The purpose of the future orchestration layer is explicit state and workflow management, not replacing deterministic business logic with agents.

---

# 11. Deterministic Business Core

The following components remain deterministic:

```text
PolicyRepository
PolicyEvaluator
CalculationEngine
ConfidenceEngine
DecisionEngine
```

## 11.1 Policy

Policy values are loaded from the policy configuration rather than being scattered throughout application code.

Example:

```text
policy_terms.json
```

The claim trace should record the policy identifier/version used for the decision.

## 11.2 Money

Financial calculations use:

```python
from decimal import Decimal
```

or integer minor units where appropriate.

Floating-point arithmetic must not be used for claim settlement calculations.

## 11.3 Calculation Order

For applicable network claims:

```text
Claimed Amount
      │
      ▼
Network Discount
      │
      ▼
Discounted Amount
      │
      ▼
Co-pay
      │
      ▼
Approved Amount
```

Every intermediate amount should be traceable.

For example:

```text
₹4,500
   │
   ▼
20% network discount = ₹900
   │
   ▼
₹3,600
   │
   ▼
10% co-pay = ₹360
   │
   ▼
₹3,240 approved
```

---

# 12. Database

## 12.1 PostgreSQL

The application uses **PostgreSQL through Supabase** for structured persistence.

Core structured data can include:

```text
claims
claim_documents
document_extractions
policy_evaluations
fraud_signals
trace_events
```

The exact schema can evolve, but domain contracts should remain independent of the database implementation.

Each processed claim should retain the policy identifier/version used for adjudication.

## 12.2 Repository Boundary

Database access should be isolated behind repositories/services.

Conceptually:

```text
Domain Service
      │
      ▼
Repository Interface
      │
      ▼
PostgreSQL / Supabase
```

This prevents SQL/database details from leaking into policy and calculation logic.

---

# 13. Document Storage

## 13.1 MVP Approach

Original medical documents are treated as **transient processing inputs**.

Conceptual lifecycle:

```text
Upload
  │
  ▼
FastAPI
  │
  ▼
Memory / Temporary File
  │
  ▼
Gemini Vision / OCR
  │
  ▼
Structured Extraction
  │
  ▼
Policy + Calculation + Decision
  │
  ▼
Persist Structured Result + Trace
  │
  ▼
Delete Temporary Document
```

The MVP does not require a permanent document bucket.

## 13.2 Storage Boundary

The document-processing code should use a storage abstraction where practical so that a future object-storage implementation can be introduced without changing business logic.

Potential future infrastructure:

```text
S3-compatible object storage
Cloud object storage
Managed document store
```

These are future scaling options, not MVP requirements.

---

# 14. Testing

The project uses pytest for:

- unit tests
- component tests
- integration tests
- policy tests
- calculation tests
- document verification tests
- extraction/normalization tests
- fraud/risk tests
- resilience tests
- confidence tests
- decision tests
- upload validation tests
- workflow regression tests

## 14.1 Verified Pytest Result

The test suite was explicitly collected with:

```powershell
pytest --collect-only -q
```

and executed with:

```powershell
pytest -q
```

Actual result:

```text
60 passed, 1 warning in 2.35s
```

Therefore:

```text
60 / 60 Pytest tests = PASS
0 failed
0 skipped
```

The warning is a non-failing `PendingDeprecationWarning` from the multipart dependency.

---

# 15. Acceptance Evaluation

The assignment contains **12 acceptance scenarios**.

They are evaluated separately from the broader pytest suite.

```text
test_cases.json
       │
       ▼
12 Acceptance Scenarios
       │
       ▼
Normal Claim Processing Pipeline
       │
       ▼
Decision + Amount + Confidence + Trace
       │
       ▼
Expected vs Actual
```

Verified result:

```text
12 / 12 acceptance cases = PASS
```

The acceptance cases cover:

```text
TC001  Missing required document
TC002  Unreadable pharmacy bill
TC003  Cross-document identity mismatch
TC004  Clean consultation approval
TC005  Waiting-period rejection
TC006  Dental partial approval
TC007  Missing pre-authorization
TC008  Per-claim limit
TC009  Same-day fraud signal
TC010  Network discount + co-pay
TC011  Graceful component failure
TC012  Excluded treatment
```

The detailed expected-vs-actual results are documented in:

```text
docs/EVAL_REPORT.md
```

---

# 16. Test Fixture Boundary

There is an important distinction between production document processing and deterministic evaluation.

## 16.1 Production Path

```text
Image / PDF
     │
     ▼
Gemini Vision / OCR
     │
     ▼
Document Classification / Extraction
     │
     ▼
Same Domain Pipeline
```

## 16.2 Deterministic Evaluation Path

```text
test_cases.json
     │
     ▼
Test Fixture Adapter
     │
     ▼
Document Classification / Extraction
     │
     ▼
Same Domain Pipeline
```

Fixture-specific information must remain confined to the test/evaluation boundary.

For example, fields such as:

```text
actual_type
fixture content
synthetic extraction values
```

must not become hidden production classifier logic.

The purpose of the fixture adapter is deterministic evaluation while preserving the same downstream domain behavior.

---

# 17. Observability

Every significant processing component should emit structured trace information containing, where applicable:

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

The trace is intended to make the final decision reconstructable.

Example:

```text
Document Verification
       │
       ▼
Policy Evaluation
       │
       ▼
Financial Calculation
       │
       ▼
Fraud Analysis
       │
       ▼
Confidence
       │
       ▼
Decision
```

Sensitive medical information should not be unnecessarily copied into logs.

Raw uploaded documents and unnecessary raw provider responses should not be persisted merely for debugging.

---

# 18. Resilience and Graceful Degradation

The system uses:

- typed errors
- bounded retries
- timeouts
- failure isolation
- deterministic failure injection for testing
- graceful degradation
- confidence reduction
- manual-review recommendation

A non-critical component failure should not automatically crash the entire claim pipeline.

The degraded state must remain visible through:

```text
trace
failed component list
degraded flag
confidence
manual-review recommendation
```

For the component-failure acceptance case, the desired behavior is:

```text
Component Failure
       │
       ▼
Record Failure
       │
       ▼
Mark Degraded
       │
       ▼
Continue Where Safe
       │
       ▼
Produce Decision
       │
       ├── reduced confidence
       ├── failed component exposed
       └── manual review recommended
```

The system must not silently hide the failure or report the same confidence as a fully healthy pipeline.

---

# 19. Frontend

## 19.1 Next.js + React + TypeScript

The frontend provides the claim submission and decision-review experience.

### Claim Submission

The UI can capture:

- member ID
- policy ID
- treatment category
- treatment date
- claimed amount
- provider information
- document uploads
- optional failure simulation for testing/demo

### Decision Review

The UI should display:

- decision
- approved amount
- confidence
- degraded state
- reasons
- document checks
- policy checks
- line-item results
- financial calculation
- fraud signals
- failed components
- trace timeline

Tailwind CSS can be used for styling without adding a separate UI framework.

---

# 20. Docker

Docker is useful for reproducible local setup and deployment.

A simple setup may contain:

```text
Frontend
   │
   ▼
Backend
   │
   ▼
PostgreSQL / Supabase
```

The architecture intentionally avoids introducing infrastructure such as Kubernetes or a service mesh for the MVP.

---

# 21. Deployment

The application is designed to remain deployable as a modular monolith.

Target deployment:

```text
Vercel
   │
   ▼
Next.js Frontend
   │
   ▼
Render
   │
   ▼
FastAPI Backend
   │
   ├──────────────► Gemini
   │
   ▼
Supabase PostgreSQL
```

The current design does not require:

```text
Kafka
Redis
Celery
RabbitMQ
Kubernetes
Microservices
Dedicated OCR infrastructure
Permanent object storage
Vector database
```

Those can be introduced only when a concrete scaling requirement justifies them.

---

# 22. Security

Minimum security requirements include:

- validate uploaded files
- restrict file sizes
- restrict accepted file types
- sanitize filenames
- never execute uploaded files
- protect Gemini/API credentials
- store credentials in environment variables
- never commit secrets to Git
- sanitize API errors
- minimize PII in logs
- avoid exposing raw provider errors to users
- delete transient documents after processing where applicable

Example environment variables:

```text
DATABASE_URL=
GEMINI_API_KEY=
GEMINI_MODEL=
GEMINI_OCR_MODEL=
GEMINI_TEMPERATURE=0.0
```

Real secrets must never be placed in source code or committed `.env` files.

---

# 23. Technology Choices Intentionally Open

The following choices are intentionally not hard-locked:

```text
Exact Gemini model/version
Production OCR preprocessing library
Embedding model
Vector database
Production object-storage vendor
Production queue
Authentication provider
Future orchestration implementation
```

Gemini is the selected current AI provider, but the provider abstraction remains intact.

Changing the AI provider should ideally require:

```text
Configuration change
        OR
New provider implementation
```

rather than a rewrite of the domain pipeline.

---

# 24. Priority Order

When choosing between implementation options, prioritize:

1. Correctness
2. Assignment acceptance criteria
3. Deterministic policy and financial logic
4. Document verification
5. Graceful failure
6. Observability
7. AI robustness
8. Testability
9. UI polish
10. Infrastructure sophistication

The project intentionally favors a simple architecture that is easy to reason about and test.

Technology is not added merely to increase architectural complexity.

---

# 25. Current Architecture

The current MVP is a modular monolith.

```text
                         Next.js
                    React + TypeScript
                              │
                              ▼
                           FastAPI
                              │
                              ▼
                  Modular Claim Orchestrator
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
        Document AI      Consistency       Fraud / Risk
             │                │                │
             ▼                │                │
      Gemini Vision / OCR      │                │
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                     Deterministic Core
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
          Policy         Calculation       Decision
          Engine           Engine           Engine
                              │
                              ▼
                         Confidence
                              │
                              ▼
                         Trace / Audit
                              │
                              ▼
                     Supabase PostgreSQL
                              │
                              ▼
                            Result
                              │
                              ▼
                              UI
```

The core architectural boundary is:

```text
AI
 │
 │ understands unstructured information
 ▼
Structured Evidence
 │
 ▼
Deterministic Domain Services
 │
 │ enforce policy and calculate money
 ▼
Decision
 │
 ▼
Trace / Persistence
```

---

# 26. Future Architecture

The current modular architecture can evolve without changing the core domain contracts.

## 26.1 Future Orchestration

```text
                         FastAPI
                            │
                            ▼
                    LangGraph StateGraph
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        Document AI   Deterministic   Fraud / Risk
          Gemini        Services        Analysis
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                    Decision / Trace
                            │
                            ▼
                         Result
```

LangGraph would own workflow state and conditional routing, while the existing domain components would continue to own:

```text
Policy
Calculation
Risk
Confidence
Decision
Persistence
Trace
```

This keeps the domain contracts stable while allowing the orchestration infrastructure to evolve.

---

# 27. Scaling Direction

At higher load, the modular monolith can be separated around stable domain contracts.

A possible future architecture is:

```text
                    Load Balancer
                          │
                          ▼
                 ┌─────────────────┐
                 │   API Instances  │
                 └────────┬────────┘
                          │
                          ▼
                  Durable Job Queue
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
          Worker 1     Worker 2     Worker N
             │            │            │
             └────────────┼────────────┘
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
           Gemini     PostgreSQL   Object Storage
```

The purpose of this evolution is to increase throughput and isolate expensive document-processing work.

The domain contracts should remain unchanged.

---

# 28. Current MVP vs Future Infrastructure

| Concern | Current MVP | Future at Higher Load |
|---|---|---|
| API | FastAPI modular monolith | Horizontally scaled API |
| Orchestration | Modular claim orchestrator | LangGraph / explicit workflow engine |
| AI | Gemini | Provider abstraction + scalable workers |
| Database | Supabase PostgreSQL | Managed PostgreSQL with replicas/partitioning as needed |
| Documents | Temporary memory/files | Object storage |
| Processing | Synchronous / request-oriented | Durable queue + worker pool |
| Trace | Structured audit events | Dedicated trace/observability store if needed |
| Deployment | Vercel + Render + Supabase | Load balancer + autoscaled services/workers |
| Service boundary | Modular code boundaries | Extract services only where justified |

The MVP does not need to prematurely implement the future infrastructure.

---

# 29. Environment Configuration

A minimal `.env.example` should contain only variables actually used by the application.

```dotenv
# Application
APP_NAME=plum-claims-ai
ENVIRONMENT=development
LOG_LEVEL=INFO

# PostgreSQL / Supabase
DATABASE_URL=

# Google Gemini
GEMINI_API_KEY=
GEMINI_MODEL=
GEMINI_OCR_MODEL=
GEMINI_TEMPERATURE=0.0
```

Do not add environment variables for technologies that are not actually used.

Never commit:

```text
.env
real API keys
database passwords
provider credentials
production secrets
```

---

# 30. Explicitly Excluded from the MVP

The following are intentionally excluded unless a real requirement appears:

```text
SQLite as a second production database
Render PostgreSQL when Supabase is already used
Redis
Kafka
Celery
RabbitMQ
S3 / Cloudinary
Pinecone
Vector database
Kubernetes
Microservices
Service mesh
Separate OCR provider
Separate LLM provider
Permanent document bucket
```

This is not because these technologies are unsuitable in general.

They are excluded because the current workload and assignment do not require the additional operational complexity.

---

# 31. Final Technology Principles

The implementation follows these principles:

### 1. AI for interpretation

```text
Unstructured document
        │
        ▼
Gemini
        │
        ▼
Structured evidence
```

### 2. Deterministic logic for business decisions

```text
Structured evidence
        │
        ▼
Policy + Calculation + Risk
        │
        ▼
Decision
```

### 3. Explicit contracts

```text
Component
   │
   ├── Input contract
   ├── Output contract
   ├── Error contract
   └── Trace contract
```

### 4. Provider independence

```text
VisionProvider
      │
      ▼
Gemini today
      │
      ▼
Another provider later
```

### 5. Simple infrastructure first

```text
Modular monolith
      │
      ▼
Measure real bottlenecks
      │
      ▼
Scale only the constrained component
```

### 6. Traceability

Every important decision should answer:

```text
What evidence was used?
What policy was applied?
What calculations were performed?
What risk signals were found?
What failed?
Why was the final decision produced?
```

---

# 32. Final Architecture Summary

The current system can be summarized as:

```text
                    ┌─────────────────────┐
                    │   Next.js Frontend  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Backend   │
                    └──────────┬──────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │ Modular Claim Orchestrator│
                 └──────────────┬────────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
      ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
      │ Gemini      │    │ Consistency │    │ Fraud / Risk│
      │ Vision / OCR│    │ Checks      │    │ Analysis    │
      └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
             │                  │                  │
             └──────────────────┼──────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ Deterministic Core  │
                    └──────────┬──────────┘
                               │
                  ┌────────────┼────────────┐
                  │            │            │
                  ▼            ▼            ▼
              Policy      Calculation   Decision
              Engine        Engine       Engine
                  │            │            │
                  └────────────┼────────────┘
                               │
                               ▼
                         Confidence
                               │
                               ▼
                         Trace / Audit
                               │
                               ▼
                    Supabase PostgreSQL
```

The architecture is intentionally modular, deterministic where correctness matters, AI-assisted where unstructured understanding is required, observable through structured traces, and simple enough to evolve without prematurely introducing distributed infrastructure.

> **Current implementation:** modular monolith with Gemini-assisted document understanding and deterministic claim adjudication.
>
> **Future evolution:** explicit stateful orchestration with LangGraph and scalable workers when workload justifies it.
