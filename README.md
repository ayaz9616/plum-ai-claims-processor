# 🏥 Plum Claims AI
### Intelligent Health Insurance Claims Processing & Decision Platform

> **AI Engineer Assignment — Plum**
>
> An explainable, policy-driven claims processing platform that validates medical documents, extracts structured information, evaluates insurance rules, detects risk signals, calculates eligible amounts, and produces auditable claim decisions with confidence scores.

**Live Application:** [https://plum-ai-claims-processor.vercel.app/](https://plum-ai-claims-processor.vercel.app/)  
**Repository:** [https://github.com/ayaz9616/plum-ai-claims-processor.git](https://github.com/ayaz9616/plum-ai-claims-processor.git)  
**Demo Video:** [YOUR_DEMO_VIDEO_URL](YOUR_DEMO_VIDEO_URL)

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

The claim then moves through a **structured processing workflow** consisting of clearly separated stages for:

1. Claim validation
2. Document verification
3. Document extraction
4. Cross-document consistency checks
5. Policy evaluation
6. Fraud/risk analysis
7. Financial calculation
8. Decision generation
9. Explainability and execution tracing

The implementation intentionally separates **AI-assisted reasoning** from **deterministic business logic**, particularly for policy enforcement and financial calculations.

The result is not just a decision, but a decision that can be inspected and reconstructed by an operations user.

---

# 🎯 What This Project Optimizes For

The architecture was designed around the actual evaluation dimensions specified in the Plum assignment:

| Evaluation Area | Weight | Design Focus |
|---|---:|---|
| System Design | **30%** | Modular workflow, separation of responsibilities, failure handling, scalability |
| Engineering Quality | **25%** | Validation, error handling, structured data, tests |
| Observability | **20%** | Full execution trace and decision reasoning |
| AI Integration | **15%** | AI for unstructured document understanding with structured outputs |
| Document Verification | **10%** | Early detection and actionable document errors |

These are the official evaluation categories from the assignment.

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
                   /          \
                 NO            YES
                 │              │
                 ▼              ▼
          Actionable Error   Extraction
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
                    Explainability / Trace
                                │
                                ▼
                         Final Response
```

### Important architectural distinction

The current implementation is **not claiming to be a fully autonomous multi-agent system**.

Instead, it uses a **modular orchestration model** in which different responsibilities are separated into processing stages/components.

This gives the system many of the engineering properties required for an agentic architecture:

- clear responsibility boundaries
- structured inputs and outputs
- independent failure points
- stage-level observability
- replaceable processing components
- deterministic/non-deterministic separation
- an explicit orchestration layer

The architecture is intentionally structured so that individual stages can later be extracted into independently executing agents or services without redesigning the complete claim workflow.

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
│        Claim Submission │ Processing │ Results              │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                  CLAIM WORKFLOW / ORCHESTRATOR                │
│                                                              │
│   Coordinates the individual processing stages and controls  │
│   early exits, failures, state transitions and final output.  │
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
                         DATABASE
```

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

This directly addresses the assignment's requirement that document problems be caught **before processing** and that the error message be specific and actionable.

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

The extraction layer is designed around the messy-document conditions described in the supplied Plum document guide, including handwritten prescriptions, phone photographs, stamps, multilingual documents, partial documents, corrections and multi-page documents.

---

# 🧩 Stage 4 — Cross-Document Validation

Extracted information from different documents is compared before policy adjudication.

For example:

```text
Prescription
Patient → Rajesh Kumar

Hospital Bill
Patient → Arjun Mehta

              ↓

        MISMATCH DETECTED
```

The workflow can then stop and surface:

> The prescription belongs to Rajesh Kumar, while the hospital bill belongs to Arjun Mehta. Please upload documents belonging to the same patient.

This is particularly important for **TC003**.

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

The assignment explicitly tests this behavior in **TC010**.

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

This preserves the distinction between:

```text
Suspicious
      ≠
Automatically fraudulent
```

TC009 specifically expects the unusual same-day pattern to result in manual review rather than automatic rejection.

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

For example:

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

This directly targets the assignment's **20% Observability** criterion.

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

This is the intended behavior for TC011 rather than returning an HTTP 500 or terminating the entire claim.

---

# 🧱 Why a Stage-Based Architecture?

The current implementation deliberately uses a modular workflow rather than claiming that every processing stage is already an autonomous agent.

This provides several useful engineering boundaries:

### 1. Independent responsibility

Each stage has a focused purpose.

### 2. Testability

Individual stages can be tested independently.

### 3. Observability

Each stage can contribute its own trace information.

### 4. Failure isolation

A failure can be associated with a specific stage.

### 5. Replaceability

An extraction implementation can eventually be replaced without rewriting policy evaluation.

### 6. Future agentization

The current boundaries provide natural candidates for future agents.

For example:

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
      │
      ├── Document Agent
      ├── Extraction Agent
      ├── Policy Agent
      ├── Fraud Agent
      └── Decision Agent
```

The important point is that **the second diagram is an architectural evolution path, not a claim about the current implementation**.

---

# 🤖 AI Usage

AI is used where it provides the most value:

```text
Unstructured Medical Documents
            ↓
        AI / Vision
            ↓
    Structured Information
            ↓
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

The assignment explicitly evaluates whether AI is integrated thoughtfully and whether model output is structured and validated.

---

# 🧪 Synthetic Medical Document Testing

To test the image/document processing workflow, I generated **synthetic medical document images** specifically for this project.

These test fixtures include examples of:

- Medical prescriptions
- Hospital bills
- Pharmacy bills
- Diagnostic reports

They are used to test:

```text
Document Classification
        ↓
Image Understanding
        ↓
Information Extraction
        ↓
Patient Matching
        ↓
Amount Extraction
        ↓
Date Extraction
        ↓
Policy Evaluation
```

The generated documents are **synthetic test data** and do not represent real patient records.

They were created to provide image-based inputs for testing instead of relying only on structured JSON test fixtures.

The supplied Plum document guide explicitly calls out difficult real-world conditions such as handwritten prescriptions, phone photos, rubber stamps, multilingual documents, partial documents, corrections and scanned multi-page documents.

---

# 🧪 Evaluation Against Official Test Cases

The project is evaluated against all **12 scenarios** provided in `test_cases.json`.

| ID | Scenario | Expected Outcome |
|---|---|---|
| TC001 | Wrong document uploaded | Early stop |
| TC002 | Unreadable document | Re-upload request |
| TC003 | Different patients | Early stop |
| TC004 | Clean consultation | `APPROVED` |
| TC005 | Diabetes waiting period | `REJECTED` |
| TC006 | Dental cosmetic exclusion | `PARTIAL` |
| TC007 | MRI without pre-auth | `REJECTED` |
| TC008 | Per-claim limit | `REJECTED` |
| TC009 | Same-day claim pattern | `MANUAL_REVIEW` |
| TC010 | Network discount + co-pay | `APPROVED` |
| TC011 | Component failure | Graceful degradation |
| TC012 | Excluded treatment | `REJECTED` |

These are the official supplied scenarios.

---

# 📊 Evaluation Report

The evaluation report does not only record:

```text
PASS / FAIL
```

For every case, the intended evaluation format captures:

```text
Test Case
Input
Expected Outcome
Actual Decision
Approved Amount
Confidence
Processing Trace
Policy Checks
Warnings
Difference / Analysis
```

This is important because the assignment explicitly asks for the **full decision output and trace for each test case**, including explanations for mismatches.

Detailed results are available in:

```text
eval_report.md
```

---

# 📋 Test Coverage

### Document Handling

- Wrong document type
- Missing documents
- Unreadable documents
- Patient mismatch
- Document extraction failures

### Policy

- Coverage
- Waiting periods
- Exclusions
- Per-claim limits
- Sub-limits
- Pre-authorization
- Network hospitals

### Financial

- Co-pay
- Network discount
- Partial approval
- Eligible amount
- Approved amount

### Risk

- Same-day claim patterns
- High-value claims
- Manual review conditions

### Reliability

- Component failure
- Degraded processing
- Reduced confidence
- Manual-review recommendation

---

# 📁 Project Structure

```text
.
├── frontend/
│
├── backend/
│   ├── workflow/
│   │   └── claim processing orchestration
│   │
│   ├── services/
│   │   ├── document processing
│   │   ├── extraction
│   │   ├── policy evaluation
│   │   ├── fraud / risk
│   │   └── calculation
│   │
│   ├── models/
│   ├── api/
│   └── ...
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evaluation/
│
├── test_documents/
│   ├── prescriptions/
│   ├── hospital_bills/
│   ├── pharmacy_bills/
│   └── diagnostic_reports/
│
├── policy_terms.json
├── test_cases.json
├── assignment.md
├── sample_documents_guide.md
├── architecture.md
├── eval_report.md
└── README.md
```

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
PostgreSQL
Git
```

---

## Clone

```bash
git clone YOUR_GITHUB_URL
cd YOUR_PROJECT_DIRECTORY
```

---

## Environment Variables

Create the required `.env` / `.env.local` files.

Example:

```env
DATABASE_URL=your_postgresql_connection_string

OPENAI_API_KEY=your_api_key

NEXT_PUBLIC_API_URL=your_backend_url
```

Additional variables required by the implementation should be added according to the backend/frontend configuration.

> Never commit credentials, database passwords, API keys or `.env` files to Git.

---

# ▶️ Run the Application

## Backend

```bash
cd backend
# install dependencies
# start backend
```

## Frontend

```bash
cd frontend
# install dependencies
# start frontend
```

Then open the configured local frontend URL.

> The exact commands used by the deployed repository are documented in the project configuration.

---

# 🧪 Run Evaluation

The official scenarios are available in:

```text
test_cases.json
```

Run the project's evaluation/test command:

```bash
npm run test:evaluation
```

or the equivalent command configured in the repository.

The resulting outputs should be compared against the expected behavior defined by the supplied test cases.

---

# 🌐 Deployment

## Production Application

**Live:** [YOUR_DEPLOYMENT_URL](YOUR_DEPLOYMENT_URL)

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

The demo follows the three scenarios requested in the assignment.

## 1. Early Document Failure

Submit a consultation claim with an incorrect document set.

Show:

```text
Uploaded Documents
        ↓
Document Verification
        ↓
Problem Detected
        ↓
Specific Error Message
        ↓
Processing Stops
```

---

## 2. Successful End-to-End Claim

Show:

```text
Claim
 ↓
Document Verification
 ↓
Extraction
 ↓
Validation
 ↓
Policy
 ↓
Risk
 ↓
Calculation
 ↓
Decision
 ↓
Full Trace
```

The important part is to keep the **full trace visible**, because observability is a major part of the evaluation.

---

## 3. Architecture Decision

A useful technical decision to discuss is:

> **Separating AI-assisted extraction/reasoning from deterministic policy evaluation and financial calculation.**

This provides a clear boundary between probabilistic AI behavior and business-critical deterministic logic.

A natural future improvement is to extract the existing processing stages into independently executing agents with explicit contracts and an orchestration layer.

---

# 🔭 Future Architecture

The current system is intentionally structured so that the processing stages can evolve into more autonomous components.

### Current

```text
                 Claim Workflow
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   Documents       Policy          Risk
   Processing      Evaluation      Analysis
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
                    Decision
```

### Possible evolution

```text
                    ┌──────────────┐
                    │ Orchestrator │
                    └───────┬──────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ Document    │      │ Policy      │      │ Risk/Fraud  │
│ Agent       │      │ Agent       │      │ Agent       │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                    ┌──────────────┐
                    │ Decision     │
                    │ Agent        │
                    └──────────────┘
```

The future model would introduce:

- explicit agent contracts
- independent execution
- agent-level retries
- timeouts
- message-based communication
- parallel execution where possible
- agent-specific observability
- independent model selection
- stronger evaluation per agent

This is an **evolution path**, not a description of the current implementation.

---

# 📈 Scaling to 10×

The current workflow is suitable for assignment-scale processing.

At significantly higher volume, the architecture could evolve toward:

```text
                   API
                    │
                    ▼
              Message Queue
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   Worker Pool  Worker Pool  Worker Pool
       │            │            │
   Documents     Extraction    Policy
       │            │            │
       └────────────┼────────────┘
                    ▼
                 Decision
                    │
                    ▼
               PostgreSQL
```

Potential improvements include:

- asynchronous document processing
- worker queues
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

---

# 🔐 Reliability & Safety Principles

The system follows several important principles:

### AI output is not automatically trusted

AI-generated structured data is validated before being used downstream.

### Financial logic is deterministic

Amounts are calculated by explicit business rules.

### Policy is configuration-driven

Policy terms come from configuration rather than being invented by the model.

### Failures are visible

A failed component should appear in the trace.

### Uncertainty reduces confidence

The system should not present a degraded decision as equivalent to a fully processed decision.

### Early problems stop early

There is no reason to continue adjudication when required documents are missing or invalid.

---

# 📚 Assignment Resources

The implementation is based on the resources supplied with the assignment:

| File | Purpose |
|---|---|
| `assignment.md` | Requirements and evaluation criteria |
| `policy_terms.json` | Policy, coverage and member configuration |
| `test_cases.json` | Official 12 evaluation scenarios |
| `sample_documents_guide.md` | Medical document formats and test variations |

The assignment explicitly states that policy logic should be read from `policy_terms.json` rather than hardcoded.

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
                 Explainable
                    Output
```

The architecture is currently implemented as a **modular orchestration workflow**, with clear processing boundaries that can be evolved into independently executing agents as the system scales.

---

## 🔗 Project Links

**Live Application:** [YOUR_DEPLOYMENT_URL](YOUR_DEPLOYMENT_URL)

**Source Code:** [YOUR_GITHUB_URL](YOUR_GITHUB_URL)

**Architecture Document:** [`architecture.md`](architecture.md)

**Evaluation Report:** [`eval_report.md`](eval_report.md)

**Demo Video:** [YOUR_DEMO_VIDEO_URL](YOUR_DEMO_VIDEO_URL)
