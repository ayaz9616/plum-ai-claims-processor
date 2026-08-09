# API Contract

## POST /api/claims
Create a claim.

Example request:
```json
{
  "member_id": "EMP001",
  "policy_id": "PLUM_GHI_2024",
  "claim_category": "CONSULTATION",
  "treatment_date": "2024-11-01",
  "claimed_amount": "1500.00",
  "documents": []
}
```

## POST /api/claims/{claim_id}/process
Process a claim and return result/status.

## GET /api/claims/{claim_id}
Return claim details/latest result.

## GET /api/claims/{claim_id}/trace
Return ordered trace events.

## GET /api/claims
List claims for operations UI.

## GET /api/policies/{policy_id}
Return safe policy representation.

## GET /api/members/{member_id}
Return member information needed for processing.

## GET /health
Return service health.

All endpoints must:
- validate input;
- use structured error codes;
- never expose stack traces;
- never expose secrets;
- avoid raw medical document logging.
