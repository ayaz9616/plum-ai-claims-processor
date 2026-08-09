# Assumptions and Interpretation Register

## A-001 — Acceptance criteria
Supplied `test_cases.json` expected outcomes are acceptance criteria. Implementation must not special-case case IDs.

## A-002 — Criticality
Critical/non-critical classification is our architecture decision based on whether trustworthy adjudication is possible.

## A-003 — Document failures
Wrong/missing/unreadable required documents block processing; they are not claim rejections.

## A-004 — Identity
Clear document identity mismatch blocks. Ambiguous identity should prefer manual review.

## A-005 — Messy documents
Handwriting, stamps, shadows and partial fields are handled with field/document confidence where possible.

## A-006 — Money
Use Decimal or minor units.

## A-007 — Confidence
Confidence is calculated from system evidence and component health.

## A-008 — Fraud
Fraud signals are risk indicators, not automatic proof of fraud.

## A-009 — Explanation
Explanation is presentation only and cannot change business facts.

## A-010 — Storage
Local storage is acceptable during development; deployed systems should use safe object/document storage.

## A-011 — Authentication
Authentication is not a primary assignment criterion. Do not let it delay core pipeline correctness.

## A-012 — Registration validation
Registration number format validation is not equivalent to external registry verification.

## A-013 — Medical scope
This is an insurance adjudication prototype, not a medical diagnosis/advice system.

## A-014 — Policy version
Persist the policy ID/version used for each claim.

## A-015 — Dates
Use date-only arithmetic for waiting periods unless timestamps are required.

## A-016 — PDFs
Treat a multi-page PDF as one document artifact and aggregate extracted evidence after page processing.

## A-017 — Optional fields
Optional missing fields do not automatically invalidate a document.

## A-018 — Network hospitals
Network membership comes from configured policy data unless a future provider registry is introduced.
