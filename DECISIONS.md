# Plum Claims AI — Architecture Decisions

## ADR-001 — Modular Monolith
**Status:** Accepted

Use one deployable application with strict internal agent/component boundaries.

Reason: assignment scope is 2–3 days and distributed microservices add operational complexity without improving the evaluated core.

Future: extract workers/services at higher load while preserving contracts.

## ADR-002 — Document Verification First
**Status:** Accepted

Required flow:
`intake -> classify -> verify -> extract -> consistency -> policy -> calculation -> fraud -> confidence -> decision`

Reason: TC001–TC003 explicitly require stopping before claim decisions.

## ADR-003 — Critical vs Non-Critical Is an Architectural Decision
**Status:** Accepted

The assignment requires graceful degradation but does not define the criticality list.

Blocking:
- core invalid input
- policy unavailable/invalid
- missing/wrong required documents
- unusable required evidence
- clear patient mismatch

Degradable:
- optional enrichment
- fraud analysis
- secondary normalization
- optional extraction

Non-critical failure must be visible and confidence-adjusted.

## ADR-004 — LLM Is Evidence Provider, Not Policy Authority
**Status:** Accepted

LLM handles:
- vision
- classification
- extraction
- normalization
- optional semantic interpretation
- optional explanation

Deterministic code handles:
- policy
- waiting periods
- exclusions
- pre-auth
- limits
- money
- fraud thresholds
- final decision
- confidence

## ADR-005 — Structured LLM Output
**Status:** Accepted

Use typed schemas/Pydantic. Bounded retries. Invalid output becomes a controlled component failure.

## ADR-006 — Decimal Financial Engine
**Status:** Accepted

Use Decimal/integer minor units. No floats. All intermediate calculations are traceable.

## ADR-007 — Line-Item Adjudication
**Status:** Accepted

Required for TC006. A claim may contain both covered and excluded line items.

## ADR-008 — Manual Review Is a Business Outcome
**Status:** Accepted

Fraud/anomaly/uncertainty can route to `MANUAL_REVIEW`; it is not a server error and not automatically rejection.

## ADR-009 — Trace Is First-Class Data
**Status:** Accepted

Every significant step emits a structured event. Operations must be able to reconstruct any decision.

## ADR-010 — Confidence Is System-Calculated
**Status:** Accepted

Confidence comes from evidence and component health, not from asking the LLM to assign a score.

## ADR-011 — Policy Is Configuration-Driven
**Status:** Accepted

Load policy from supplied `policy_terms.json` via a repository/configuration layer. Do not scatter policy values.

## ADR-012 — No Test-ID Special Cases
**Status:** Accepted

Never write logic such as:
`if test_case_id == "TC010": ...`

Tests validate generic business behavior.

## ADR-013 — Policy/Test Discrepancies Are Documented
**Status:** Accepted

The supplied policy and acceptance expectations need careful interpretation in places such as limits/sub-limits and TC006/TC010.

Preserve source data. Implement generic rule precedence. Document the chosen interpretation. Do not hide it or encode test IDs.

## ADR-014 — Parallel Independent Extraction
**Status:** Accepted

Independent document extractions may run concurrently after verification. Dependent operations remain sequential.

## ADR-015 — Deterministic Failure Injection
**Status:** Accepted

TC011 uses an explicit failure-injection mechanism, not random process crashes.

## ADR-016 — Separate Processing Status From Decision
**Status:** Accepted

Example:
`processing_status=PROCESSING_DEGRADED`, `decision=APPROVED`.

## ADR-017 — Explanation Cannot Modify Facts
**Status:** Accepted

LLM-generated prose can only express already validated structured evidence.

## ADR-018 — Privacy by Default
**Status:** Accepted

No raw medical documents or unnecessary PII in logs. Secrets never enter source control.

## ADR-019 — Evidence-First Explanations
**Status:** Accepted

Every reason references concrete evidence and rule results.

## ADR-020 — Scope Discipline
**Status:** Accepted

Do not build Kubernetes, service mesh, elaborate auth, or unnecessary distributed infrastructure during the assignment.

## ADR-021 — 10x Scaling
**Status:** Accepted

At higher volume, move long-running work behind queues and worker pools. Keep component contracts stable.
