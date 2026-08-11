# Plum Claims AI — Architecture Decisions & Assumptions

This document records the architectural decisions, assumptions, trade-offs, and implementation constraints that shape Plum Claims AI.

The purpose is to make important design choices explicit so that another engineer can understand:

- why the system is structured this way;
- which behavior is intentional;
- which assumptions are being made;
- which parts are deterministic versus probabilistic;
- how failures are handled;
- what can change without rewriting the domain;
- and how the system can evolve at higher scale.

The decisions below describe the current MVP unless explicitly marked as future evolution.

---

# Architecture Decisions

## ADR-001 — Modular Monolith

**Status:** Accepted

Use one deployable application with strict internal component/service boundaries.

### Decision

The current system remains a modular monolith rather than being split into independently deployed microservices.

The internal architecture still separates responsibilities such as:

- document processing;
- document verification;
- normalization;
- consistency checking;
- policy evaluation;
- financial calculation;
- fraud/risk analysis;
- confidence calculation;
- decision generation;
- trace/audit persistence.

### Reason

The current workload does not justify the operational complexity of distributed services.

A modular monolith provides:

- simpler local development;
- simpler deployment;
- easier debugging;
- lower network overhead;
- easier end-to-end testing;
- clear internal contracts.

### Future

At higher load, long-running or independently scalable components can be extracted into workers/services while preserving the existing contracts.

---

## ADR-002 — Document Verification First

**Status:** Accepted

Required flow:

```text
intake
  ↓
classify
  ↓
verify
  ↓
extract
  ↓
consistency
  ↓
policy
  ↓
calculation
  ↓
fraud
  ↓
confidence
  ↓
decision
```

### Decision

Required-document verification happens before expensive extraction and before claim adjudication.

### Reason

A claim should not proceed through policy evaluation when required evidence is missing, wrong, or unusable.

Examples include:

- missing hospital bill;
- wrong document type;
- unreadable required document;
- unusable critical evidence.

### Outcome

The user receives an actionable error rather than an apparently valid claim decision based on incomplete evidence.

---

## ADR-003 — Critical vs Non-Critical Is an Architectural Decision

**Status:** Accepted

The system explicitly classifies processing components according to whether their failure should block a claim.

### Blocking failures

The following are considered blocking:

- invalid core input;
- policy unavailable or invalid;
- missing required documents;
- wrong required document;
- unusable required evidence;
- clear patient/document identity mismatch;
- other failures that make a safe adjudication impossible.

### Degradable failures

The following may be treated as degradable where sufficient evidence remains:

- optional enrichment;
- fraud analysis;
- secondary normalization;
- optional extraction;
- other non-essential analysis.

### Decision

A non-critical component failure must not silently disappear.

The system should:

```text
record failure
     ↓
mark processing degraded
     ↓
reduce confidence
     ↓
continue where safe
     ↓
recommend manual review where appropriate
```

### Reason

The architecture must distinguish:

```text
"the claim cannot safely be processed"
```

from:

```text
"one analysis component was unavailable, but enough evidence remains"
```

---

## ADR-004 — LLM Is an Evidence Provider, Not Policy Authority

**Status:** Accepted

### LLM responsibilities

The LLM/vision provider may handle:

- document vision;
- classification;
- OCR-assisted extraction;
- normalization;
- handwriting interpretation;
- optional semantic interpretation;
- optional explanation generation.

### Deterministic responsibilities

Application code remains authoritative for:

- policy;
- waiting periods;
- exclusions;
- pre-authorization;
- limits;
- sub-limits;
- co-pay;
- network discounts;
- money;
- fraud thresholds;
- final decision;
- confidence calculation.

### Reason

Probabilistic model output should not be the final authority for business-critical financial and policy rules.

The architecture therefore follows:

```text
Unstructured evidence
        ↓
AI interpretation
        ↓
Structured evidence
        ↓
Validation
        ↓
Deterministic business rules
        ↓
Decision
```

---

## ADR-005 — Structured LLM Output

**Status:** Accepted

### Decision

LLM output is converted into typed structures and validated with schemas/Pydantic before entering the domain layer.

### Requirements

- explicit output schemas;
- validation;
- bounded retries;
- controlled fallback;
- structured error handling.

### Failure behavior

If the provider returns invalid structured output:

```text
invalid provider output
        ↓
validation failure
        ↓
controlled component failure
```

The system must not silently accept malformed model output.

---

## ADR-006 — Decimal Financial Engine

**Status:** Accepted

### Decision

Use `Decimal` or integer minor units for financial calculations.

Do not use binary floating-point arithmetic for claim settlement.

### Requirements

Every important intermediate value should be traceable.

Example:

```text
Claimed Amount
      ↓
Network Discount
      ↓
Eligible Amount
      ↓
Co-pay
      ↓
Approved Amount
```

### Reason

Financial calculations must be deterministic, reproducible, and free from avoidable floating-point precision issues.

---

## ADR-007 — Line-Item Adjudication

**Status:** Accepted

### Decision

Claims containing multiple bill line items are evaluated at line-item level when required by policy.

A claim may contain:

```text
Covered item
Excluded item
```

at the same time.

### Example

```text
Root Canal        ₹8,000 → Covered
Teeth Whitening   ₹4,000 → Excluded
```

The final result may therefore be:

```text
PARTIAL
Approved Amount: ₹8,000
```

### Reason

Claim-level all-or-nothing treatment would lose important policy information.

---

## ADR-008 — Manual Review Is a Business Outcome

**Status:** Accepted

### Decision

`MANUAL_REVIEW` is a valid claim-processing outcome.

It is not:

- a server error;
- an HTTP failure;
- an automatic rejection;
- an indication that the application crashed.

### Examples

Manual review may be appropriate when:

- fraud risk is high;
- important analysis is unavailable;
- evidence is ambiguous;
- document quality creates uncertainty;
- financial evidence conflicts;
- confidence falls below the safe automatic-decision threshold.

---

## ADR-009 — Trace Is First-Class Data

**Status:** Accepted

### Decision

Every significant processing step emits a structured event.

A trace event should contain information such as:

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
retry count
```

### Reason

Operations should be able to reconstruct how a decision was produced without reading application logs line by line.

---

## ADR-010 — Confidence Is System-Calculated

**Status:** Accepted

### Decision

Confidence is calculated by the application from evidence quality and component health.

The LLM is not asked:

> "What confidence should the system assign to this claim?"

### Inputs may include

- document quality;
- evidence completeness;
- identity consistency;
- component failures;
- policy certainty;
- fraud/risk analysis availability;
- conflicting evidence;
- processing degradation.

### Reason

Confidence should represent the health of the processing pipeline rather than a model's subjective self-rating.

---

## ADR-011 — Policy Is Configuration-Driven

**Status:** Accepted

### Decision

Policy terms are loaded from configuration through a repository/configuration layer.

The supplied policy configuration contains concepts such as:

- coverage;
- sub-limits;
- co-pay;
- network discounts;
- waiting periods;
- exclusions;
- pre-authorization;
- network hospitals;
- fraud thresholds;
- claim limits;
- document requirements;
- member information.

### Reason

Policy values should not be scattered throughout application code or hidden inside prompts.

---

## ADR-012 — No Test-ID Special Cases

**Status:** Accepted

### Decision

Business logic must never contain test-specific branches such as:

```python
if test_case_id == "TC010":
    ...
```

### Reason

Acceptance tests should validate generic business behavior.

The implementation should pass because the underlying rules are correct, not because the system recognizes a fixture identifier.

---

## ADR-013 — Policy/Test Discrepancies Are Documented

**Status:** Accepted

### Decision

Where policy configuration and acceptance expectations require interpretation, the source data is preserved and the chosen rule precedence is documented.

### Examples

Potential ambiguity can arise around:

- limits versus sub-limits;
- line-item exclusions;
- financial calculation ordering;
- expected outcomes for mixed covered/excluded items.

### Rule

Do not:

- modify source policy simply to make a test pass;
- encode test IDs;
- hide an ambiguity.

Instead:

```text
preserve source data
       ↓
define generic rule precedence
       ↓
document interpretation
       ↓
implement consistently
```

---

## ADR-014 — Parallel Independent Extraction

**Status:** Accepted

### Decision

Independent document-extraction operations may run concurrently after required-document verification.

Dependent operations remain sequential.

Example:

```text
                 Document Verification
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Prescription     Bill         Lab Report
      Extraction     Extraction     Extraction
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                  Consistency Check
```

### Reason

Independent AI calls can be parallelized for latency improvement without changing domain behavior.

---

## ADR-015 — Deterministic Failure Injection

**Status:** Accepted

### Decision

Failure scenarios are injected explicitly and deterministically during testing.

The system should not depend on random process crashes to validate resilience.

### Reason

Deterministic failure injection makes graceful-degradation behavior:

- repeatable;
- testable;
- debuggable;
- safe to demonstrate.

---

## ADR-016 — Separate Processing Status From Decision

**Status:** Accepted

### Decision

Processing health and claim decision are represented separately.

Example:

```text
processing_status = PROCESSING_DEGRADED
decision          = APPROVED
```

### Reason

A claim can still be approved when a non-critical component fails, but that does not mean the processing pipeline was completely healthy.

This distinction also supports:

- confidence reduction;
- manual-review recommendations;
- transparent operations;
- accurate trace reporting.

---

## ADR-017 — Explanation Cannot Modify Facts

**Status:** Accepted

### Decision

LLM-generated explanatory prose may only describe already validated structured evidence.

The explanation layer cannot:

- invent a policy rule;
- change an amount;
- change a treatment date;
- create a new fraud signal;
- alter the final decision;
- introduce unsupported evidence.

### Flow

```text
Validated Facts
      ↓
Explanation Generator
      ↓
Human-readable Explanation
```

not:

```text
LLM Explanation
      ↓
Business Decision
```

---

## ADR-018 — Privacy by Default

**Status:** Accepted

### Decision

Medical information and PII are treated as sensitive by default.

The system should:

- avoid raw medical documents in logs;
- avoid unnecessary PII in trace messages;
- protect API credentials;
- keep secrets out of source control;
- delete transient documents after processing where applicable;
- sanitize external/provider errors before returning them to users.

### Reason

Claims processing involves sensitive personal and medical information, so observability must not become a reason to over-retain sensitive data.

---

## ADR-019 — Evidence-First Explanations

**Status:** Accepted

### Decision

Every important explanation should reference concrete evidence or rule results.

Example:

```text
Reason:
Claim rejected because treatment falls within the waiting period.

Evidence:
Treatment Date = 2024-10-15
Coverage Start = 2024-11-30
Waiting Period = 30 days
```

### Reason

Evidence-backed explanations are easier for operations teams to trust, verify, and audit.

---

## ADR-020 — Scope Discipline

**Status:** Accepted

### Decision

The MVP intentionally avoids infrastructure that does not solve a current problem.

Not required in the current architecture:

- Kubernetes;
- service mesh;
- elaborate authentication infrastructure;
- Kafka;
- Redis;
- Celery;
- RabbitMQ;
- premature microservices;
- permanent object storage;
- vector databases.

### Reason

The system should remain understandable, testable, and deployable.

Infrastructure should be introduced in response to an actual workload or reliability requirement.

---

## ADR-021 — 10× Scaling

**Status:** Accepted

At significantly higher volume, long-running claim processing should move behind a durable queue and worker pool.

Possible future architecture:

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
             ▼            ▼            ▼
          Worker 1     Worker 2     Worker N
             │            │            │
             └────────────┼────────────┘
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
           Gemini     PostgreSQL   Object Storage
```

### Principle

Keep domain/component contracts stable while changing infrastructure around them.

---

## ADR-022 — Current Orchestration Is Modular; LangGraph Is Future Evolution

**Status:** Accepted

### Decision

The current MVP uses a modular claim orchestrator.

LangGraph is considered a future option for explicit stateful workflow orchestration.

### Current

```text
FastAPI
   │
   ▼
Modular Claim Orchestrator
   │
   ├── Document Processing
   ├── Verification
   ├── Consistency
   ├── Policy
   ├── Calculation
   ├── Fraud / Risk
   ├── Confidence
   └── Decision
```

### Future

```text
FastAPI
   │
   ▼
LangGraph StateGraph
   │
   ├── Document Nodes
   ├── Policy Nodes
   ├── Risk Nodes
   ├── Recovery Paths
   └── Human Review Paths
```

### Reason

The existing component contracts provide a clean foundation for future stateful orchestration without pretending that the current MVP already depends on LangGraph.

---

## ADR-023 — AI Provider Abstraction

**Status:** Accepted

### Decision

Google Gemini is the current AI provider, but provider-specific behavior is isolated behind interfaces/abstractions such as:

```text
LLMProvider
VisionProvider
```

### Reason

The application should not require a domain-layer rewrite if the model provider changes.

Conceptually:

```text
VisionProvider
      │
      ▼
Gemini Vision Provider
```

A future provider can implement the same contract.

---

## ADR-024 — AI for Unstructured Information, Code for Business Rules

**Status:** Accepted

### Decision

AI is used where interpretation is difficult to express deterministically.

Application code remains authoritative where correctness must be exact.

### AI-oriented work

- document understanding;
- OCR;
- classification;
- extraction;
- normalization;
- semantic interpretation;
- optional explanation.

### Deterministic work

- policy rules;
- waiting periods;
- exclusions;
- limits;
- pre-authorization;
- money;
- fraud thresholds;
- confidence;
- final decision.

### Reason

This minimizes the blast radius of model uncertainty.

---

## ADR-025 — Temporary Document Processing

**Status:** Accepted

### Decision

Original uploaded medical documents are treated as transient processing inputs in the MVP.

Conceptual lifecycle:

```text
Upload
  ↓
Temporary memory/file
  ↓
Vision / OCR
  ↓
Structured extraction
  ↓
Claim processing
  ↓
Structured result / trace
  ↓
Temporary document cleanup
```

### Reason

The current application does not require a permanent document repository to perform the core workflow.

### Future

If audit, retention, reprocessing, or regulatory requirements require durable document storage, an object-storage layer can be introduced behind a storage abstraction.

---

## ADR-026 — Structured Persistence Is Separate From Raw Document Storage

**Status:** Accepted

### Decision

A database, where used by the application, is intended for structured claim/application state rather than automatically implying permanent storage of raw medical documents.

Possible structured records include:

```text
claims
claim_documents
document_extractions
policy_evaluations
fraud_signals
trace_events
```

Raw medical files and structured claim state therefore have different lifecycles.

### Reason

Structured operational data and raw document retention have different storage, privacy, and lifecycle requirements.

---

## ADR-027 — Repository Boundary for Persistence

**Status:** Accepted

### Decision

Database access is isolated behind repositories/services rather than embedded directly in policy or calculation logic.

Conceptually:

```text
Domain Service
      ↓
Repository Interface
      ↓
PostgreSQL / Supabase
```

### Reason

This keeps persistence concerns separate from business rules and makes future storage changes less invasive.

---

## ADR-028 — Verification Before Expensive AI Processing

**Status:** Accepted

### Decision

The system performs cheap deterministic checks before expensive AI calls whenever possible.

Preferred ordering:

```text
Basic validation
      ↓
Required-document verification
      ↓
Document quality checks
      ↓
AI extraction
```

### Reason

There is no reason to spend model/API resources processing a claim that is already invalid because required evidence is absent.

This also improves latency and cost efficiency.

---

## ADR-029 — Early Exit for Unsafe Adjudication

**Status:** Accepted

### Decision

The workflow may terminate early when the available evidence is insufficient for a safe decision.

Examples:

```text
Missing required document
Wrong required document
Clear identity mismatch
Invalid policy configuration
Unusable critical evidence
```

### Reason

Continuing into policy evaluation with invalid evidence can produce misleading decisions.

---

## ADR-030 — Policy Evaluation Is Independent of the LLM

**Status:** Accepted

### Decision

The policy engine should be capable of evaluating structured claim data without needing an LLM call.

### Reason

This makes policy behavior:

- deterministic;
- unit-testable;
- reproducible;
- easier to audit;
- less affected by provider availability.

The AI layer supplies evidence; the policy engine applies rules.

---

## ADR-031 — Fraud Signals Are Not Automatically Fraud Verdicts

**Status:** Accepted

### Decision

Risk analysis produces signals/scores rather than automatically treating every anomaly as fraud.

Example:

```text
4th same-day claim
       ↓
High-risk signal
       ↓
MANUAL_REVIEW
```

### Reason

An anomaly is evidence requiring attention, not necessarily proof of fraudulent behavior.

---

## ADR-032 — Degraded Processing Must Remain Visible

**Status:** Accepted

### Decision

If processing continues after a non-critical failure, the final result must retain the degraded state.

The response should expose, where applicable:

```text
degraded = true
failed_components = [...]
confidence = reduced
manual_review_recommended = true
```

### Reason

A user or operator must not mistake a degraded result for a fully healthy result.

---

## ADR-033 — Trace and Decision Are Separate Concepts

**Status:** Accepted

### Decision

The trace records **how the system processed the claim**.

The decision records **what the system concluded**.

Example:

```text
Trace
 ├── document verification
 ├── extraction
 ├── consistency
 ├── policy
 ├── calculation
 ├── fraud
 └── confidence

Decision
 ├── outcome
 ├── approved amount
 ├── reasons
 └── confidence
```

### Reason

Separating these concepts keeps both operational observability and user-facing results clean.

---

## ADR-034 — Test Fixtures Must Not Become Production Logic

**Status:** Accepted

### Decision

Synthetic documents and deterministic evaluation fixtures may provide controlled inputs during testing, but fixture-specific behavior must remain isolated from production business rules.

### Prohibited

```python
if test_case_id == "TC006":
    ...
```

### Allowed

```text
test fixture
   ↓
normal input boundary
   ↓
same production workflow
```

### Reason

The acceptance suite should validate the real workflow rather than a collection of test-specific branches.

---

## ADR-035 — Acceptance Tests and Unit Tests Are Different Layers

**Status:** Accepted

### Decision

The project maintains both:

```text
Acceptance scenarios
        +
Unit / component / integration tests
```

The acceptance layer verifies representative end-to-end behavior.

The pytest suite verifies individual contracts and regression behavior.

### Current verified result

```text
12 / 12 acceptance cases = PASS

60 / 60 pytest tests = PASS
```

### Reason

A green unit suite does not by itself prove end-to-end acceptance behavior, and acceptance scenarios do not replace detailed component tests.

---

# Assumptions

The following assumptions are part of the current system design. They should be revisited if requirements change.

## A-001 — Policy Configuration Is Authoritative

`policy_terms.json` is treated as the source of policy values for the current application.

If a future production policy service becomes authoritative, the repository/configuration boundary should remain stable.

---

## A-002 — Member Identity Is Available

The system assumes that a claim can be associated with a known member/policy identity.

Where document identity is available, it should be checked against the claim/member identity.

---

## A-003 — Required Documents Depend on Claim Type

Different claim categories can require different document sets.

For example, a consultation may require a prescription and hospital bill.

The system should not assume one universal document set for every claim.

---

## A-004 — Document Quality Can Be Uncertain

Images may be:

- blurry;
- handwritten;
- skewed;
- partially unreadable;
- photographed under poor lighting;
- multilingual;
- incomplete.

Therefore extraction must be treated as probabilistic evidence rather than guaranteed truth.

---

## A-005 — Structured Extraction Can Fail

AI/provider calls can:

- time out;
- return malformed output;
- return incomplete fields;
- fail to classify a document;
- fail to read critical information.

The system therefore requires bounded retries and controlled failure handling.

---

## A-006 — A Claim Can Contain Multiple Documents

The workflow assumes that a claim may contain multiple related documents and that their contents can be compared.

---

## A-007 — A Claim Can Contain Multiple Line Items

Financial adjudication may need to evaluate each bill line separately.

A single claim can therefore result in:

```text
fully covered
partially covered
fully excluded
```

depending on the policy and evidence.

---

## A-008 — Policy Rules May Interact

Rules such as:

```text
coverage
waiting period
exclusion
pre-authorization
limit
sub-limit
network discount
co-pay
```

may apply together.

The system therefore requires an explicit precedence/order rather than assuming rules are independent.

---

## A-009 — Financial Order Matters

Where multiple financial transformations apply, their order affects the final result.

For example:

```text
network discount
        ↓
eligible amount
        ↓
co-pay
        ↓
approved amount
```

The calculation engine therefore defines and traces the order explicitly.

---

## A-010 — Fraud Analysis Is Risk-Oriented

Fraud analysis produces signals that may influence routing and confidence.

It is not assumed that every high-risk signal is proof of fraudulent behavior.

---

## A-011 — Manual Review Is Available

The architecture assumes that some claims cannot or should not be automatically resolved.

A downstream operations/review process is therefore treated as a valid business outcome.

---

## A-012 — Non-Critical Failure Can Still Permit a Decision

If enough validated evidence remains, the system may continue after a non-critical component failure.

Such a decision must be marked degraded and have appropriately reduced confidence.

---

## A-013 — Critical Failure Prevents Safe Adjudication

If a failure removes evidence required to safely determine eligibility or calculate the claim, the system should block or route the claim for review rather than guess.

---

## A-014 — Confidence Is Relative, Not a Statistical Probability

The current confidence value is a system health/evidence-quality indicator.

It should not be interpreted as a mathematically calibrated probability of correctness unless a separate calibration process is introduced.

---

## A-015 — Provider Output Is Untrusted Until Validated

Even when the model is expected to return structured JSON, the application assumes that the response can be malformed or incomplete.

---

## A-016 — Original Documents Are Not Required for Every Processing Step

Once required structured evidence has been extracted and validated, downstream deterministic components should operate on structured domain objects rather than repeatedly calling the document model.

---

## A-017 — Temporary Files Must Be Cleaned Up

Transient document files are assumed to have a bounded lifecycle.

Processing code should clean them up after use, including appropriate failure paths.

---

## A-018 — Sensitive Data Should Not Be Used as Debug Output

Logs and traces should contain enough information for diagnosis without unnecessarily copying medical documents or sensitive PII.

---

## A-019 — The Current Application Is a Single Logical Claim Workflow

The MVP assumes one claim is processed as one logical workflow.

Concurrency and background processing can be added later without changing the core domain contracts.

---

## A-020 — External AI Calls Are a Reliability Boundary

Gemini/provider calls can be slower or less reliable than local deterministic operations.

Therefore:

- timeouts should be bounded;
- retries should be limited;
- provider errors should be isolated;
- degraded processing should be explicit.

---

## A-021 — AI Model Version Can Change

The exact AI model may change over time.

Therefore model/provider configuration should be isolated and, where relevant, recorded in processing metadata.

---

## A-022 — Policy Version Should Be Traceable

A decision should be associated with the policy configuration/version used to produce it.

This is important if policy rules change later.

---

## A-023 — Deterministic Domain Logic Should Be Reproducible

Given the same validated inputs, policy version, and configuration, deterministic components should produce the same output.

This is essential for debugging and auditability.

---

## A-024 — Evaluation Uses Controlled Fixtures

The acceptance scenarios use controlled fixtures so that expected outcomes are reproducible.

Fixture-specific behavior must remain outside production business logic.

---

## A-025 — Synthetic Documents Are Test Data

Generated medical documents used for testing are assumed to be synthetic and are not treated as real patient records.

---

## A-026 — Database and Raw Document Storage Have Different Lifecycles

Structured claim state may be persisted when required by the application, while raw medical documents may remain transient in the MVP.

Introducing a database does not automatically imply permanent raw-document retention.

---

## A-027 — Database Availability Is a Separate Failure Mode

If structured persistence is unavailable, the application should distinguish:

```text
claim-processing failure
```

from:

```text
persistence failure
```

The appropriate response depends on whether the result can safely be returned and whether persistence is mandatory for that workflow.

---

## A-028 — API Layer Should Remain Thin

HTTP/API concerns should not own policy logic, financial calculations, or model-specific reasoning.

The API should delegate to domain services.

---

## A-029 — UI Does Not Determine the Decision

The frontend displays and submits claim information.

It is not trusted to calculate the final approved amount or override backend policy decisions.

---

## A-030 — Future Agentization Does Not Change Domain Ownership

If the system evolves toward agents, agents should call stable domain contracts rather than duplicating policy and financial logic.

For example:

```text
Policy Agent
     ↓
Policy Service
     ↓
Deterministic Policy Rules
```

not:

```text
Policy Agent
     ↓
Free-form LLM decision
```

---

## A-031 — Higher Load Justifies Infrastructure Evolution

Queues, workers, object storage, replicas, caching, and service extraction are assumed to be justified only when actual workload characteristics require them.

---

## A-032 — The MVP Optimizes for Correctness Before Distributed Complexity

The current architecture assumes that correctness, observability, deterministic business rules, and failure handling provide more value than premature distributed infrastructure.

---

# Decision Relationships

The major decisions reinforce each other:

```text
Modular Monolith
       │
       ├───────────────┐
       ▼               ▼
Explicit Contracts   Deterministic Core
       │               │
       ▼               ▼
Replaceable AI     Reproducible Decisions
       │               │
       └───────┬───────┘
               ▼
          Structured Trace
               │
               ▼
        Explainable Result
               │
               ▼
        Graceful Degradation
               │
               ▼
       Future Scalability
```

The central principle is:

> **Use AI where interpretation is valuable, use deterministic software where correctness must be exact, and keep enough structured evidence and trace information to explain every decision.**

---

# Future Evolution

These decisions are designed to remain valid as the system grows.

A possible evolution is:

```text
Current MVP

Next.js
   │
   ▼
FastAPI
   │
   ▼
Modular Claim Orchestrator
   │
   ▼
Domain Services
   │
   ▼
PostgreSQL / Structured Persistence


Higher Load

Load Balancer
   │
   ▼
API Instances
   │
   ▼
Durable Queue
   │
   ▼
Worker Pool
   │
   ├── Document Workers
   ├── Policy Workers
   ├── Risk Workers
   └── Decision Workers
```

The implementation should preserve the same contracts while changing the execution infrastructure around them.

---

# Summary

The architecture is intentionally built around the following rules:

1. **Keep the current deployment simple.**
2. **Keep domain responsibilities modular.**
3. **Verify required documents before adjudication.**
4. **Use AI for unstructured evidence, not as the policy authority.**
5. **Validate all structured AI output.**
6. **Use deterministic financial calculations.**
7. **Evaluate mixed claims at line-item level where required.**
8. **Treat manual review as a legitimate business outcome.**
9. **Make confidence and degradation explicit.**
10. **Make the processing trace reconstructable.**
11. **Keep policy configuration-driven.**
12. **Never encode test IDs into business logic.**
13. **Keep fixture behavior outside production logic.**
14. **Protect medical data and secrets by default.**
15. **Keep explanations grounded in validated evidence.**
16. **Separate structured persistence from raw-document retention.**
17. **Keep provider-specific AI logic behind abstractions.**
18. **Scale infrastructure only when workload justifies it.**
19. **Preserve contracts when extracting workers/services.**
20. **Treat LangGraph/agentization as a future orchestration evolution, not a prerequisite for the current MVP.**
