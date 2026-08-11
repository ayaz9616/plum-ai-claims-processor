# 🏥 Plum Claims AI

### Intelligent Health Insurance Claims Processing & Decision Platform

> An explainable, policy-driven claims processing platform that validates medical documents, extracts structured information, evaluates insurance rules, detects risk signals, calculates eligible amounts, and produces auditable claim decisions with confidence scores.

**Live Application:**  
https://plum-ai-claims-processor.vercel.app/

**Repository:**  
https://github.com/ayaz9616/plum-ai-claims-processor

**Demo Video:**  
_To be added for submission._

---

## 📌 Overview

Plum Claims AI automates the processing of employee health-insurance claims from document submission to final decision.

The system accepts:

- Member details
- Policy information
- Claim category
- Treatment date
- Claimed amount
- Medical documents such as prescriptions, hospital bills, pharmacy bills and diagnostic reports

The claim moves through a structured processing workflow consisting of:

1. Claim validation
2. Document verification
3. Document extraction
4. Cross-document consistency checks
5. Policy evaluation
6. Fraud/risk analysis
7. Financial calculation
8. Decision generation
9. Explainability and execution tracing

The implementation intentionally separates **AI-assisted document understanding** from **deterministic business logic**, particularly for policy enforcement and financial calculations.

The result is not just a decision, but a decision that can be inspected and reconstructed by an operations user.

---

# 🎯 What This Project Optimizes For

The architecture is designed around five practical engineering goals:

| Area | Design Focus |
|---|---|
| System design | Modular workflow, separation of responsibilities, failure handling, scalability |
| Engineering quality | Validation, error handling, structured data, tests |
| Observability | Full execution trace and decision reasoning |
| AI integration | AI for unstructured document understanding with structured outputs |
| Document verification | Early detection and actionable document errors |

The design therefore prioritizes:

```text
Reliability
    +
Explainability
    +
Deterministic Policy Enforcement
    +
AI-assisted Document Understanding
    +
Observability
    +
Graceful Failure Handling
```

---

# 🧠 Architecture Philosophy

Rather than implementing the entire system as one large AI prompt, the backend is organized as a **stage-based orchestration pipeline**.

Conceptually:

```text
                         CLAIM
                           │
                           ▼
                  ┌─────────────────┐
                  │ Claim Validation│
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │    Document     │
                  │   Verification  │
                  └────────┬────────┘
                           │
                    Valid Documents?
                       /         \
                     NO           YES
                     │             │
                     ▼             ▼
              Actionable Error  Extraction
              + Early Stop          │
                                    ▼
                           Cross-Document
                            Validation
                                    │
                                    ▼
                           Policy Evaluation
                                    │
                                    ▼
                             Risk / Fraud
                              Analysis
                                    │
                                    ▼
                            Financial Rules
                             & Calculation
                                    │
                                    ▼
                               Decision
                                    │
                                    ▼
                          Explainability /
                               Trace
                                    │
                                    ▼
                            Final Response
```

## Important architectural distinction

The current implementation is **not claiming to be a fully autonomous multi-agent system**.

Instead, it uses a **modular orchestration model** in which different responsibilities are separated into processing stages/components.

This gives the system:

- clear responsibility boundaries
- structured inputs and outputs
- independent failure points
- stage-level observability
- replaceable processing components
- deterministic/non-deterministic separation
- an explicit orchestration layer

These boundaries also provide a clean evolution path toward independently executing agents or services later, without claiming that such a topology is already implemented.

---

# 🏗️ High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                                                              │
│  Claims Dashboard │ New Claim │ Decision │ Processing Trace │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                         API LAYER                            │
│                                                              │
│       Claim Submission │ Processing │ Results               │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                  CLAIM WORKFLOW / ORCHESTRATOR               │
│                                                              │
│ Coordinates processing stages, early exits, failures, state  │
│ transitions and final output.                                │
└────────────┬─────────────┬─────────────┬─────────────┬───────┘
             │             │             │             │
             ▼             ▼             ▼             ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
      │ Document   │ │ Extraction │ │ Consistency│ │   Policy   │
      │ Validation │ │ Processing │ │ Validation │ │ Evaluation │
      └────────────┘ └────────────┘ └────────────┘ └────────────┘
             │             │             │             │
             └─────────────┴─────────────┴─────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Risk / Fraud     │
                    │ Analysis         │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Calculation      │
                    │ Engine           │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Decision         │
                    │ Generation       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Execution Trace  │
                    │ & Explainability │
                    └────────┬─────────┘
                             │
                             ▼
                    Structured Result
```

> **Database note:** PostgreSQL/Supabase is available as the structured persistence layer where the current implementation uses it. Original medical documents are treated as transient processing inputs rather than permanent document objects.

---

# 🔄 Claim Processing Workflow

A claim is processed as a sequence of explicit stages.

## Stage 1 — Claim Intake

The system validates the basic claim payload:

```text
Member
Policy
Category
Treatment Date
Claim Amount
Documents
```

Invalid requests are rejected before expensive processing begins.

---

## Stage 2 — Document Verification

The system first checks whether the uploaded documents satisfy the requirements for the selected claim category.

For example:

```text
CONSULTATION

Required:
├── PRESCRIPTION
└── HOSPITAL_BILL

Optional:
├── LAB_REPORT
└── DIAGNOSTIC_REPORT
```

If a user uploads:

```text
PRESCRIPTION
PRESCRIPTION
```

the workflow stops before claim adjudication.

The system explains:

```text
Uploaded:
PRESCRIPTION

Still required:
HOSPITAL_BILL

Action:
Please upload the hospital bill to continue.
```

This keeps document problems visible **before claim adjudication** and makes errors specific and actionable.

---

# 📄 Stage 3 — Document Understanding & Extraction

Once the document set passes verification, the system extracts structured information from the uploaded documents.

Depending on document type, this can include:

```text
Patient
Doctor
Registration Number
Hospital / Clinic
Diagnosis
Treatment
Prescription
Test
Date
Line Items
Amounts
Total
```

Example normalized representation:

```json
{
  "document_type": "PRESCRIPTION",
  "patient_name": "Rajesh Kumar",
  "doctor_name": "Dr. Arun Sharma",
  "doctor_registration": "KA/45678/2015",
  "diagnosis": "Viral Fever",
  "date": "2024-11-01"
}
```

The extraction layer is designed around difficult document conditions such as:

- handwritten prescriptions
- phone photographs
- stamps
- multilingual documents
- partial documents
- corrections
- multi-page documents

---

# 🧩 Stage 4 — Cross-Document Validation

Extracted information from different documents is compared before policy adjudication.

For example:

```text
Prescription
Patient → Rajesh Kumar

Hospital Bill
Patient → Arjun Mehta

        │
        ▼
MISMATCH DETECTED
```

The workflow can then stop and surface:

> The prescription belongs to Rajesh Kumar, while the hospital bill belongs to Arjun Mehta. Please upload documents belonging to the same patient.

This is particularly important for preventing claims from being adjudicated with inconsistent patient documents.

---

# 📜 Stage 5 — Policy Evaluation

Policy evaluation is driven by the supplied:

```text
policy_terms.json
```

rather than embedding policy values directly into an LLM prompt.

The configuration contains:

- Coverage
- Sub-limits
- Co-pay
- Network discounts
- Waiting periods
- Exclusions
- Pre-authorization
- Network hospitals
- Claim thresholds
- Fraud thresholds
- Document requirements
- Member information

This keeps business rules configurable and makes policy changes independent from the AI layer.

---

# 💰 Stage 6 — Financial Calculation

Financial calculations are handled deterministically.

For example:

```text
₹4,500 Claim
      │
      ▼
20% Network Discount
      │
      ▼
₹3,600 Eligible Amount
      │
      ▼
10% Co-pay
      │
      ▼
₹360 Deduction
      │
      ▼
₹3,240 Approved
```

The calculation order is important.

This ordering is covered by the financial test suite and is important for keeping settlement calculations reproducible.

The LLM is therefore not trusted to perform financial arithmetic or independently modify policy thresholds.

---

# 🚨 Stage 7 — Risk & Fraud Analysis

The workflow also evaluates available risk signals.

Examples include:

- Multiple same-day claims
- Monthly claim frequency
- High-value claims
- Claim history
- Suspicious document signals
- Other available claim-level anomalies

A risk signal does not necessarily mean rejection.

For example:

```text
Multiple same-day claims
          │
          ▼
      Risk Signal
          │
          ▼
     MANUAL_REVIEW
```

This preserves the distinction:

```text
Suspicious
    ≠
Automatically fraudulent
```

The unusual same-day pattern is routed to manual review rather than being treated as an automatic fraud verdict.

---

# 🧠 Stage 8 — Decision Generation

The workflow aggregates the results of previous stages and produces one of:

```text
APPROVED
PARTIAL
REJECTED
MANUAL_REVIEW
```

Every decision is accompanied by:

```text
Decision
Approved Amount
Reason
Confidence
Policy Checks
Risk Signals
Calculation
Warnings
Processing Trace
```

---

# 🔍 Explainability-First Design

One of the most important design choices is that the system does not expose only the final answer.

Instead:

```text
Final Decision
      │
      ├── Document Verification
      ├── Extraction Results
      ├── Consistency Checks
      ├── Policy Checks
      ├── Risk Signals
      ├── Financial Calculation
      ├── Component Status
      └── Confidence
```

This means an operations user can reconstruct **why** the system reached a particular decision.

Example:

```text
CLAIM CLM-XXXX

✓ Member verified
✓ Required documents present
✓ Patient identity matched
✓ Prescription extracted
✓ Hospital bill extracted
✓ Treatment covered
✓ Waiting period passed
✓ Claim within limit
✓ No high-risk signal

Calculation:
₹4,500
- ₹900 network discount
= ₹3,600
- ₹360 co-pay
= ₹3,240

DECISION: APPROVED
CONFIDENCE: 0.94
```

This makes the system observable and the final decision reconstructable.

---

# 🛡️ Graceful Degradation

The workflow treats component failures as **processing states**, not simply application crashes.

Conceptually:

```text
             Component Failure
                    │
                    ▼
          ┌─────────────────────┐
          │ Capture failure     │
          │ Continue if safe    │
          │ Reduce confidence   │
          │ Surface warning     │
          └──────────┬──────────┘
                     │
                     ▼
              Continue Workflow
                     │
                     ▼
               Decision / Review
```

For example:

```text
Decision: APPROVED

Confidence: 0.71

Warnings:
- Risk analysis component unavailable
- Complete processing could not be performed
- Manual review recommended
```

This allows the system to surface a degraded result rather than simply returning an HTTP 500 or terminating the entire claim.

---

# 🧱 Why a Stage-Based Architecture?

The current implementation deliberately uses a modular workflow rather than claiming that every processing stage is already an autonomous agent.

## 1. Independent responsibility

Each stage has a focused purpose.

## 2. Testability

Individual stages can be tested independently.

## 3. Observability

Each stage can contribute its own trace information.

## 4. Failure isolation

A failure can be associated with a specific stage.

## 5. Replaceability

An extraction implementation can eventually be replaced without rewriting policy evaluation.

## 6. Future agentization

The current boundaries provide natural candidates for future agents.

```text
CURRENT

Workflow
 ├── Document Verification
 ├── Extraction
 ├── Policy Evaluation
 ├── Fraud Analysis
 └── Decision

FUTURE

Orchestrator
 ├── Document Agent
 ├── Extraction Agent
 ├── Policy Agent
 ├── Fraud Agent
 └── Decision Agent
```

The second diagram is an architectural evolution path, **not a claim about the current implementation**.

---

# 🤖 AI Usage

AI is used where it provides the most value:

```text
Unstructured Medical Documents
            │
            ▼
        AI / Vision
            │
            ▼
    Structured Information
            │
            ▼
   Deterministic Processing
```

AI-assisted areas include:

- Document understanding
- Document classification
- Medical information extraction
- Handling inconsistent layouts
- Semantic interpretation
- Decision explanation

Deterministic components remain responsible for:

- Policy limits
- Waiting periods
- Required documents
- Exclusions
- Pre-authorization requirements
- Financial calculations
- Network discounts
- Co-pay

This separation makes the system less dependent on free-form model behavior.

---

# 🧪 Synthetic Medical Document Testing

Synthetic medical document images were generated specifically for this project.

These test fixtures include examples of:

- Medical prescriptions
- Hospital bills
- Pharmacy bills
- Diagnostic reports

They are used to test:

```text
Document Classification
        │
        ▼
Image Understanding
        │
        ▼
Information Extraction
        │
        ▼
Patient Matching
        │
        ▼
Amount Extraction
        │
        ▼
Date Extraction
        │
        ▼
Policy Evaluation
```

The generated documents are **synthetic test data** and do not represent real patient records.

They provide image-based inputs in addition to structured test fixtures.

---

# 🧪 Verification & Acceptance Coverage

The project includes a set of representative acceptance scenarios in `test_cases.json`. They cover the major claim-processing paths below.

| ID | Scenario | Expected Outcome |
|---|---|---|
| TC001 | Wrong document uploaded | Early stop / blocked |
| TC002 | Unreadable document | Re-upload / quality failure |
| TC003 | Different patients | Early stop / blocked |
| TC004 | Clean consultation | `APPROVED` |
| TC005 | Diabetes waiting period | `REJECTED` |
| TC006 | Dental cosmetic exclusion | `PARTIAL` |
| TC007 | MRI without pre-auth | `REJECTED` |
| TC008 | Per-claim limit | `REJECTED` |
| TC009 | Same-day claim pattern | `MANUAL_REVIEW` |
| TC010 | Network discount + co-pay | `APPROVED` |
| TC011 | Component failure | Graceful degradation |
| TC012 | Excluded treatment | `REJECTED` |

---

# 📊 Automated Verification Results

The repository has been verified with the automated test suite and the representative acceptance scenarios.

## Pytest

The test suite was collected with:

```bash
pytest --collect-only -q
```

and executed with:

```bash
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

The warning was a non-failing `PendingDeprecationWarning` from the multipart dependency.

## Acceptance Evaluation

The official acceptance scenarios were also evaluated:

```text
12 / 12 acceptance cases = PASS
```

The detailed evaluation report records expected vs actual outcomes, decisions, amounts, traces and relevant observations.

See:

```text
eval_report.md
```

---

# 📋 Acceptance Test Coverage

## Document Handling

- Wrong document type
- Missing documents
- Unreadable documents
- Patient mismatch
- Document extraction failures

## Policy

- Coverage
- Waiting periods
- Exclusions
- Per-claim limits
- Sub-limits
- Pre-authorization
- Network hospitals

## Financial

- Co-pay
- Network discount
- Partial approval
- Eligible amount
- Approved amount

## Risk

- Same-day claim patterns
- High-value claims
- Manual review conditions

## Reliability

- Component failure
- Degraded processing
- Reduced confidence
- Manual-review recommendation

---

# 📁 Project Structure

The repository is organized around the actual modular backend and test suite.

```text
.
├── frontend/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── infrastructure/
│   │   ├── workflow/
│   │   └── ...
│   │
│   └── ...
│
├── tests/
│   ├── conftest.py
│   ├── test_claim_state_regression.py
│   ├── test_config.py
│   ├── test_extraction_normalize.py
│   ├── test_fraud.py
│   ├── test_health.py
│   ├── test_ocr.py
│   ├── test_policy_evaluator.py
│   ├── test_policy_loader.py
│   ├── test_uploads.py
│   └── test_workflow_p0.py
│
├── policy_terms.json
├── test_cases.json
├── assignment.md
├── sample_documents_guide.md
├── architecture.md
├── eval_report.md
├── TECHNOLOGY_STACK.md
└── README.md
```

The test suite contains **60 individual pytest tests** across the test modules above.

---

# ⚙️ Configuration

The system uses the supplied policy configuration rather than embedding policy values directly into application logic.

Important configuration:

```text
policy_terms.json
```

It contains:

```text
Coverage
Sub-limits
Co-pay
Network discounts
Waiting periods
Exclusions
Pre-authorization
Network hospitals
Claim thresholds
Fraud thresholds
Member roster
Document requirements
```

This makes the processing workflow configurable and avoids coupling the application to a single hardcoded policy.

---

# 🚀 Local Setup

## Prerequisites

```text
Node.js
npm
Python 3.x
Git
```

A PostgreSQL-compatible database is required only for the persistence paths actually enabled by the application.

## Clone

```bash
git clone https://github.com/ayaz9616/plum-ai-claims-processor.git
cd plum-ai-claims-processor
```

## Backend

```bash
cd backend
```

Create and activate a Python virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies using the repository's dependency file.

Then start the FastAPI application using the configured backend entry point.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open the local frontend URL shown by Next.js.

> The exact backend start command should follow the entry point currently present in the repository.

---

# 🔐 Environment Variables

Use environment variables for provider credentials and deployment configuration.

Example:

```env
DATABASE_URL=your_postgresql_connection_string

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model
GEMINI_OCR_MODEL=your_gemini_ocr_model
GEMINI_TEMPERATURE=0.0

NEXT_PUBLIC_API_URL=http://localhost:8000
```

Only variables actually read by the current application should be configured.

> Never commit credentials, database passwords, API keys or `.env` files to Git.

---

# 🧪 Run Tests

Run the full pytest suite:

```bash
pytest -q
```

Expected verified result:

```text
60 passed, 1 warning in 2.35s
```

To inspect the tests collected:

```bash
pytest --collect-only -q
```

---

# 🌐 Deployment

## Live Application

https://plum-ai-claims-processor.vercel.app/

## Source Code

https://github.com/ayaz9616/plum-ai-claims-processor

## Demo Video

_To be added for submission._

The deployed application allows a reviewer to:

1. Open the claims interface
2. Submit a claim
3. Upload medical documents
4. Start processing
5. Observe the processing result
6. Inspect the final decision
7. Review confidence
8. Inspect the execution trace
9. Understand the policy checks and calculation

---

# 🎥 Recommended Demo Flow

The demo should cover the three important behaviors requested in the assignment.

## 1. Early Document Failure

Submit a consultation claim with an incorrect document set.

Show:

```text
Uploaded Documents
        │
        ▼
Document Verification
        │
        ▼
Problem Detected
        │
        ▼
Specific Error Message
        │
        ▼
Processing Stops
```

---

## 2. Successful End-to-End Claim

Show:

```text
Claim
  │
  ▼
Document Verification
  │
  ▼
Extraction
  │
  ▼
Validation
  │
  ▼
Policy
  │
  ▼
Risk
  │
  ▼
Calculation
  │
  ▼
Decision
  │
  ▼
Full Trace
```

Keep the **full trace visible**, because observability is a major part of the evaluation.

---

## 3. Architecture Decision

A useful technical decision to discuss is:

> **Separating AI-assisted extraction/reasoning from deterministic policy evaluation and financial calculation.**

This provides a clear boundary between probabilistic AI behavior and business-critical deterministic logic.

A natural future improvement is to extract the existing processing stages into independently executing agents with explicit contracts and an orchestration layer.

---

# 🔭 Future Architecture

The current system is intentionally structured so that the processing stages can evolve into more autonomous components.

## Current

```text
                 Claim Workflow
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   Documents        Policy          Risk
   Processing       Evaluation      Analysis
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
                    Decision
```

## Possible Evolution

```text
                    ┌──────────────┐
                    │ Orchestrator │
                    └───────┬──────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ Document    │      │ Policy      │      │ Risk / Fraud│
│ Agent       │      │ Agent       │      │ Agent       │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Decision     │
                    │ Agent        │
                    └──────────────┘
```

The future model could introduce:

- explicit agent contracts
- independent execution
- agent-level retries
- timeouts
- message-based communication
- parallel execution where appropriate
- agent-specific observability
- independent model selection
- stronger evaluation per agent

This is an **evolution path**, not a description of the current implementation.

---

# 📈 Scaling to 10×

The current workflow is suitable for the present application workload.

At significantly higher volume, the architecture could evolve toward:

```text
                    Load Balancer
                          │
                          ▼
                    API Instances
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

Potential improvements include:

- asynchronous document processing
- durable worker queues
- horizontal scaling
- connection pooling
- database indexing
- distributed tracing
- caching policy configurations
- model routing
- retries and circuit breakers
- rate limiting
- background processing
- independent scaling of expensive AI workloads
- permanent object storage for documents where required

The MVP intentionally does not introduce this infrastructure prematurely.

---

# 🔐 Reliability & Safety Principles

The system follows several important principles.

### AI output is not automatically trusted

AI-generated structured data is validated before being used downstream.

### Financial logic is deterministic

Amounts are calculated by explicit business rules.

### Policy is configuration-driven

Policy terms come from configuration rather than being invented by the model.

### Failures are visible

A failed component should appear in the trace.

### Uncertainty reduces confidence

A degraded decision should not be presented as equivalent to a fully processed decision.

### Early problems stop early

There is no reason to continue adjudication when required documents are missing or invalid.

---

# 📚 Project Resources

The implementation is driven by the project's requirements, policy configuration, test fixtures and design documents:

| File | Purpose |
|---|---|
| `assignment.md` | Product requirements and constraints |
| `policy_terms.json` | Policy, coverage and member configuration |
| `test_cases.json` | Official 12 evaluation scenarios |
| `sample_documents_guide.md` | Medical document formats and test variations |

---

# 📊 Engineering Trade-offs

A few deliberate trade-offs were made.

### AI vs deterministic logic

AI is used for unstructured information; deterministic code handles policy and money.

### Modular workflow vs premature microservices

The current system keeps the processing stages within a manageable workflow rather than introducing network overhead and operational complexity before it is necessary.

### Explainability vs minimal output

More trace information is retained because claims decisions need to be auditable.

### Graceful degradation vs strict failure

The workflow attempts to continue when it is safe to do so, while reducing confidence and surfacing manual review when important information is unavailable.

### Current architecture vs future agentization

The current stage boundaries provide a clean migration path toward independent agents without pretending that the current implementation already has that topology.

---

# 🏁 Conclusion

Plum Claims AI is designed around a simple principle:

> **Automating a claims decision is not enough; the system must also explain how it reached that decision, identify when it is uncertain, and fail safely when parts of the pipeline are unavailable.**

The current implementation therefore focuses on:

```text
              ┌──────────────────┐
              │ Claim Processing │
              └────────┬─────────┘
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
   Document          Policy           Risk
   Intelligence      Reasoning        Analysis
       │               │                │
       └───────────────┼────────────────┘
                       ▼
                 Deterministic
                  Calculation
                       │
                       ▼
                    Decision
                       │
                       ▼
                   Full Trace
                       │
                       ▼
                Explainable Output
```

The architecture is currently implemented as a **modular orchestration workflow**, with clear processing boundaries that can evolve into independently executing agents as the system scales.

---

## 🔗 Project Links

**Live Application:**  
https://plum-ai-claims-processor.vercel.app/

**Source Code:**  
https://github.com/ayaz9616/plum-ai-claims-processor

**Architecture Document:**  
`architecture.md`

**Technology Stack:**  
`TECHNOLOGY_STACK.md`

**Evaluation Report:**  
`eval_report.md`

**Demo Video:**  
_To be added for submission._
