# GitHub Copilot Instructions — Plum Claims AI

Before significant implementation work, read:
1. `PLAN.md`
2. `DECISIONS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/COMPONENT_CONTRACTS.md`
5. `docs/ASSUMPTIONS.md`
6. supplied assignment resources: `assignment.md`, `policy_terms.json`, `test_cases.json`, `sample_documents_guide.md`, `README.md`

## Mandatory rules

- Document verification comes before adjudication.
- Policy values must come from configuration.
- Never hardcode test-case IDs.
- LLMs interpret evidence; deterministic code decides policy and money.
- LLM outputs must be structured and schema-validated.
- Use Decimal/integer minor units for money.
- Support line-item adjudication.
- `MANUAL_REVIEW` is a business outcome.
- Non-critical failures degrade safely.
- Critical failures stop or route to manual review.
- Every claim gets an auditable trace.
- Confidence is explainable.
- Explanation generation cannot alter business facts.
- Never expose raw stack traces.
- Never log unnecessary medical PII.
- Do not silently change source policy/test data.

## Forbidden

Never write:
```python
if test_case_id == "TC010":
    ...
```

Never let an LLM directly determine:
- approved amount
- arithmetic
- waiting period
- policy limits
- final decision

Never write:
```python
except Exception:
    pass
```

## Workflow before editing

1. inspect existing repository;
2. read the relevant contract;
3. identify impacted tests;
4. make the smallest coherent change;
5. run relevant tests;
6. update docs if architecture changes.

Do not rewrite unrelated code.

## Testing

Run:
```bash
pytest
python scripts/run_evals.py
```

Never claim a test passes unless it was actually executed.

## Priority

1. correctness
2. acceptance behavior
3. deterministic policy/calculation
4. graceful failure
5. observability
6. AI robustness
7. UI polish
8. infrastructure sophistication
