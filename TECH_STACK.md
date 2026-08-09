# Plum Claims AI — Technology Stack

## 1. Purpose

This is the concise technology-stack reference for the Plum Claims AI assignment.

It complements:- `assignment.md`- `policy_terms.json`- `test_cases.json`- `sample_documents_guide.md`- `README.md`- `PLAN.md`- `DECISIONS.md`- `docs/ARCHITECTURE.md`- `docs/COMPONENT_CONTRACTS.md`

The original assignment files remain authoritative. This document records the implementation stack and boundaries chosen for the project.

---

## 2. Stack Overview

| Area | Technology | Status ||---|---|---|| Frontend | Next.js + React + TypeScript | Core demo UI || Styling | Tailwind CSS | Recommended || Backend API | Python + FastAPI | Core || Validation | Pydantic | Core || Orchestration | LangGraph | Planned core orchestration layer || LLM | **Google Gemini** | Selected implementation provider || Vision/OCR | **Google Gemini multimodal vision** | Selected implementation provider || AI abstraction | `LLMProvider` / `VisionProvider` | Required architecture || Policy Engine | Python deterministic rules | Core || Calculation | Python `Decimal` | Core || Database | Supabase PostgreSQL | Core || Local database | Same Supabase PostgreSQL | Required || Document storage | Temporary memory / temporary file | Core || Permanent document storage | None for MVP | Deliberately excluded || Testing | pytest | Core || Evaluation | `scripts/run_evals.py` | Core || Observability | Structured trace/audit events | Core || Containerization | Docker | Recommended || Deployment | Vercel Free + Render Free + Supabase Free | Target |

---

## 3. Backend

### Python

Use Python for:- claim orchestration- document-processing services- policy evaluation- financial calculation- fraud analysis- confidence calculation- API implementation- evaluation runner

### FastAPI

Initial API:

```textGET  /healthPOST /api/claimsPOST /api/claims/{claim_id}/processGET  /api/claimsGET  /api/claims/{claim_id}GET  /api/claims/{claim_id}/traceGET  /api/policies/{policy_id}GET  /api/members/{member_id}```

---

## 4. Data Validation

Use Pydantic for important domain/API contracts:

```textClaimSubmissionClaimDocumentArtifactDocumentClassificationDocumentExtractionDocumentVerificationResultConsistencyResultPolicyEvaluationRuleResultFinancialCalculationResultFraudAnalysisConfidenceResultDecisionResultTraceEvent```

Invalid structured AI output must never silently enter business logic.

---

# 5. AI / LLM — Google Gemini

## Selected provider

The implementation will use **Google Gemini** as the primary LLM provider.

Gemini is intended for:- multimodal document understanding- document classification- OCR-assisted extraction- handwritten text interpretation- messy document understanding- field extraction- normalization- semantic consistency analysis where appropriate- optional explanation generation

The exact Gemini model should be configurable through environment/configuration rather than hardcoded throughout the application.

Example configuration concept:

```textGEMINI_API_KEYGEMINI_MODEL```

Never commit credentials to Git.

---

## 6. Gemini Vision / OCR

Use **Google Gemini multimodal vision** for document image/PDF understanding and OCR-assisted extraction.

The supplied document guide explicitly expects handling of difficult medical documents, including:

- handwritten prescriptions- phone-camera photographs- low-quality images- skew- shadows- stamps- partially illegible text- regional/multilingual documents- multi-page PDFs- altered/corrected documents

The Gemini vision layer should therefore be designed around structured extraction prompts and typed outputs rather than plain free-form text.

Example conceptual flow:

```textImage / PDF    ↓Gemini Multimodal Vision    ↓OCR + Document Understanding    ↓Structured Extraction    ↓Pydantic Validation    ↓Domain Pipeline```

Gemini should return structured information such as:

```textdocument_typedocument_qualitypatient_namedoctor_namedatesdiagnosisline_itemsamountsregistration_numbersconfidence per fieldevidence/signals```

Do not allow the Gemini response to directly determine financial approval.

---

# 7. AI Provider Abstraction — IMPORTANT

Although Gemini is the selected implementation provider, the application must **not be tightly coupled to Gemini**.

Use interfaces/abstractions such as:

```textLLMProviderVisionProvider```

Conceptually:

```text                 LLMProvider                     |              GeminiProvider                     |                 Google Gemini```

and:

```text                VisionProvider                     |          GeminiVisionProvider                     |                 Gemini```

The rest of the application consumes provider-neutral structured domain objects.

This means we can later replace Gemini with another provider without rewriting:- document verification- policy engine- calculation engine- fraud logic- confidence engine- decision engine- database- UI

Possible future implementations:

```textOpenAIVisionProviderClaudeVisionProviderAzureVisionProviderOtherVisionProvider```

These are future alternatives, not current requirements.

---

# 8. LLM Responsibilities vs Deterministic Responsibilities

### AI / Gemini may handle

```textDocument classificationOCR / vision extractionHandwriting interpretationMessy document understandingMedical-document field extractionNormalizationSemantic consistency analysisOptional explanation generation```

### AI must NOT be the authoritative source for

```textArithmeticClaim amount calculationPolicy limitsWaiting-period arithmeticExclusion rule executionPre-authorization threshold calculationSub-limit calculationCo-pay calculationNetwork discount calculationFinal approved amountFinal deterministic policy decision```

Those responsibilities remain deterministic application logic.

This separation is mandatory for correctness and testability.

---

# 9. LangGraph

## Status

**Planned as the core orchestration/state layer after the deterministic foundation is working.**

Do not rewrite the existing domain components into LLM agents.

LangGraph should coordinate:- claim state- node execution- conditional routing- failures- degraded processing- manual-review paths- final result aggregation

Target workflow:

```textClaim State    |    vInput Validation    |    vDocument Classification    |    vDocument Verification    |    +---- blocking ----> Blocked    |    vDocument Extraction    |    vCross-Document Consistency    |    +---- mismatch ----> Blocked / Manual Review    |    vPolicy Evaluation    |    vFinancial Calculation    |    vFraud Analysis    |    +---- high risk ----> Manual Review    |    vConfidence    |    vDecision    |    vTrace / Result```

Not every LangGraph node should use an LLM.

Recommended classification:

| Node | AI? ||---|---|| Input validation | No || Document classification | Gemini || Document verification | Deterministic || Document extraction | Gemini || Consistency | Hybrid || Policy evaluation | Deterministic || Financial calculation | Deterministic || Fraud analysis | Hybrid || Confidence | Deterministic || Decision | Deterministic || Explanation | Optional Gemini || Trace | Deterministic |

---

# 10. Deterministic Business Core

These components remain deterministic:

```textPolicyRepositoryPolicyEvaluatorCalculationEngineConfidenceEngineDecisionEngine```

### Policy

Load values from:

```textpolicy_terms.json```

Do not scatter policy values through source code.

### Money

Use:

```pythonDecimal```

or integer minor units.

Never use floating-point arithmetic for claim calculations.

### Calculation order

For applicable network claims:

```textclaimed amount    ↓network discount    ↓discounted amount    ↓co-pay    ↓approved amount```

Every intermediate calculation must be traceable.

---

# 11. Database

### Recommended

PostgreSQL.

Core structured data:

```textclaimsdocumentsdocument_extractionspolicy_evaluationsfraud_signalstrace_events```

Persist the policy ID/version used for each claim.

### Local development

SQLite or an in-memory repository may be used where it speeds up early development/testing.

Do not let the development choice leak into domain logic.

---

# 12. Document Storage

### Development

Safe local storage is acceptable.

Requirements:- validate file type- validate size- sanitize filenames- never execute uploaded files- isolate uploaded content- avoid unnecessary duplication

### Deployment

Use an object-storage abstraction so the implementation can later move to S3-compatible/object storage without changing the business layer.

---

# 13. Testing

Use pytest for:

- unit tests- component tests- orchestrator integration tests- policy tests- calculation tests- document verification tests- resilience tests- confidence tests- decision tests

The supplied 12 test cases are acceptance scenarios.

---

# 14. Evaluation Runner

Create:

```textscripts/run_evals.py```

Responsibilities:

1. load `test_cases.json`2. construct evaluation inputs3. execute the normal processing pipeline4. collect decision5. collect approved amount6. collect confidence7. collect degraded state8. collect failed components9. collect full trace10. compare actual vs expected11. produce machine-readable output12. update `docs/EVAL_REPORT.md`

Never implement test-specific production logic.

---

# 15. Test Fixture Boundary

Production document processing:

```textImage/PDF   ↓Gemini Vision/OCR   ↓DocumentClassification / Extraction   ↓Domain pipeline```

Deterministic evaluation:

```texttest_cases.json   ↓Test Fixture Adapter   ↓DocumentClassification / Extraction   ↓Same domain pipeline```

`actual_type` and fixture `content` may be used by the **test-fixture adapter only**.

They must NOT become production classifier logic.

---

# 16. Observability

Every significant component emits a structured trace event containing, where applicable:

```texttrace_idclaim_idstepcomponentstatusdurationsafe input summarysafe output summaryevidenceerrorretry_count```

Do not log unnecessary medical PII or raw documents.

Gemini requests/responses should also be represented safely in traces without storing unnecessary sensitive content.

---

# 17. Resilience

Use:

- typed errors- bounded retries- timeouts- failure isolation- deterministic failure injection- graceful degradation- confidence reduction- manual-review recommendation

TC011 requires a component to fail while processing continues where safe.

The failure must be visible in:- trace- failed component list- degraded state- confidence- manual-review recommendation

---

# 18. Frontend

### Next.js + React + TypeScript

The UI should provide:

### Claim submission

- member ID- policy ID- treatment category- treatment date- claimed amount- provider information- document upload- optional failure simulation for testing/demo

### Decision review

Display:

- decision- approved amount- confidence- degraded state- reasons- document checks- policy checks- line-item results- financial calculation- fraud signals- failed components- trace timeline

Tailwind CSS is recommended for rapid implementation.

---

# 19. Docker

Docker is recommended for reproducible local setup.

Potential services:

```textbackendfrontendpostgres```

Do not introduce Kubernetes, service meshes, or unnecessary distributed infrastructure for this assignment.

---

# 20. Deployment

Deployment platform is intentionally not locked yet.

Keep the application deployable as a modular monolith.

Future scaling can introduce:

```textAPI  ↓Queue  ↓Worker Pool  ↓PostgreSQL  ↓Object Storage```

without changing core domain contracts.

---

# 21. Security

Minimum requirements:

- validate uploads- sanitize filenames- restrict file sizes/types- never execute uploaded files- protect Gemini/API secrets- use environment variables for credentials- no secrets committed to Git- sanitized API errors- minimal PII in logs- do not expose raw AI provider errors to users

---

# 22. Technology Choices Intentionally Open

The following are NOT locked yet:

```textExact Gemini model/versionProduction OCR preprocessing libraryEmbedding modelVector databaseDeployment providerProduction object-storage vendorProduction queueAuthentication provider```

**Gemini is the selected provider, but the provider abstraction must remain intact.**

This means changing the Gemini model/provider later should require configuration or a new provider implementation rather than a rewrite of the domain pipeline.

---

# 23. Priority Order

When choosing between implementation options:

1. Correctness2. Assignment acceptance criteria3. Deterministic policy/financial logic4. Document verification5. Graceful failure6. Observability7. AI robustness8. Testability9. UI polish10. Infrastructure sophistication

Do not add technology merely to make the architecture look complex.

---

# 24. Final Target Architecture

```text                    Next.js                       |                    FastAPI                       |              Claim Orchestrator                       |                    LangGraph                       |       +---------------+---------------+       |               |               | Document AI     Consistency       Fraud AI       |               |               | Gemini Vision      Hybrid          Hybrid OCR/Extraction       |               |               |       +---------------+---------------+                       |              Deterministic Core                       |       +---------------+---------------+       |               |               |     Policy       Calculation      Decision     Engine          Engine          Engine       |               |               |       +---------------+---------------+                       |                  Confidence                       |                 Trace / Audit                       |                    Result                       |                      UI```

Implementation should proceed incrementally while preserving these boundaries.

25. Final Deployment and Simplicity Rules

Single database provider

Use Supabase PostgreSQL from the beginning, both locally and in production.

Do not use SQLite locally and switch later.

Local FastAPI
      ↓
Supabase PostgreSQL

Production FastAPI
      ↓
Supabase PostgreSQL

The application uses:

DATABASE_URL=

Do not hardcode credentials.

Temporary documents

Original medical documents are transient processing inputs only.

Upload
  ↓
FastAPI
  ↓
memory / temporary file
  ↓
Gemini Vision/OCR
  ↓
structured extraction
  ↓
policy + calculation + decision
  ↓
persist structured result + trace
  ↓
delete temporary document

No S3, Cloudinary, or permanent document bucket is required for the MVP.

Target $0 deployment

Vercel Free
  ↓
Next.js frontend
  ↓
Render Free
  ↓
FastAPI + LangGraph
  ├── Gemini
  └── Supabase PostgreSQL

Keep the implementation simple enough to understand and deploy without unnecessary infrastructure.

Required environment template

The root .env.example should contain only variables actually used:

# Application
APP_NAME=plum-claims-ai
ENVIRONMENT=development
LOG_LEVEL=INFO

# Supabase PostgreSQL
DATABASE_URL=

# Google Gemini
GEMINI_API_KEY=
GEMINI_MODEL=
GEMINI_OCR_MODEL=
GEMINI_TEMPERATURE=0.0

Use one GEMINI_API_KEY unless the actual Gemini setup requires separate credentials.

Never commit .env or real secrets.

Explicitly excluded unless required

SQLite
Render PostgreSQL
Redis
Kafka
Celery
RabbitMQ
S3
Cloudinary
Pinecone
Vector DB
Kubernetes
Microservices
Separate OCR provider
Separate LLM provider

The project is a modular monolith.

Final architecture

                         Next.js
                    React + TypeScript
                           |
                           v
                        FastAPI
                           |
                       LangGraph
                    Claim StateGraph
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
       Document AI    Consistency    Fraud Analysis
             |
       Gemini Vision/OCR
             |
             +-------------+-------------+
                           |
                  Deterministic Core
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          Policy      Calculation     Decision
          Engine         Engine        Engine
                           |
                      Confidence
                           |
                       Trace/Audit
                           |
                           v
                  Supabase PostgreSQL
                           |
                           v
                         Result
                           |
                           v
                           UI

Core principle

Gemini
  → understands unstructured documents

LangGraph
  → orchestrates state and workflow

Deterministic services
  → enforce policy and financial correctness

Supabase PostgreSQL
  → stores structured results and audit data

Temporary memory/files
  → hold documents only while processing

Next.js
  → user interface

FastAPI
  → backend API

Prefer the simplest implementation that satisfies the assignment. Do not introduce infrastructure merely for architectural complexity.