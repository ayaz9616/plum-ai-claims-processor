# Component Contracts

Every significant component must have a typed input/output contract, error contract, and trace behavior.

## ClaimIntake
Input: `ClaimSubmission`
Output: `Claim`
Errors: `InvalidClaimInput`, `UnsupportedClaimCategory`
Severity: critical

## PolicyRepository
Input: `policy_id`
Output: immutable `PolicySnapshot`
Errors: `PolicyNotFound`, `PolicySchemaInvalid`, `PolicyLoadError`
Severity: critical

## DocumentClassifier
Input: `DocumentArtifact`
Output: `DocumentClassification`
Fields: document ID, type, confidence, quality, signals
Errors: classification timeout/error, invalid model output
Severity: critical when needed to establish required document presence

## DocumentVerifier
Input: category + policy document requirements + classifications
Output: `DocumentVerificationResult`
Responsibilities: required/received comparison, wrong/missing/unreadable detection, actionable message
Severity: critical

## DocumentExtractor
Input: `DocumentArtifact`
Output: document-specific extraction schema with field confidence
Errors: timeout, invalid extraction, unsupported type
Severity: depends on whether essential evidence is recoverable

## ConsistencyAgent
Input: all relevant extracted evidence
Output: `ConsistencyResult`
Checks: identity, dates, provider/doctor, amounts, treatment consistency
Severity: critical for clear identity mismatch

## PolicyEvaluator
Input: policy snapshot + normalized claim evidence
Output: `PolicyEvaluation`
Checks: coverage, waiting, exclusion, pre-auth, limits, policy validity
Severity: critical

## CalculationEngine
Input: `FinancialCalculationInput`
Output: `FinancialCalculationResult`
Rules: Decimal, deterministic, ordered, traceable
Errors: invalid amount/rule
Severity: critical

## FraudSignalAgent
Input: claim, history, fraud thresholds, document signals
Output: `FraudAnalysis`
Errors: timeout/analysis error
Severity: normally non-critical

## ConfidenceEngine
Input: quality, extraction, consistency, policy, failures, fraud availability
Output: `ConfidenceResult`
Must expose factors
Severity: deterministic fallback required

## DecisionEngine
Input: all validated results
Output: `DecisionResult`
Responsibilities: precedence, decision, reasons, approved amount
Severity: critical

## TraceManager
Input: `TraceEvent`
Output: persisted event
Responsibilities: audit trail
Trace storage failure must be surfaced and monitored

## ClaimOrchestrator
Input: `Claim`
Output: `ClaimProcessingResult`
Responsibilities: order, failure isolation, aggregation, trace
Only fatal orchestration errors should reach the API

## LLMProvider
Input: provider-neutral structured request
Output: provider-neutral structured response
Must support timeout, bounded retry and validation
Must never directly decide policy/money

## FailureInjector
Input: component identifier + claim config
Output: deterministic failure trigger
Purpose: TC011
