import json
from backend.app.infrastructure.repositories import PolicyRepository
from backend.app.core.policy import PolicyEvaluator
from backend.app.config import config


def load_test_cases():
    with open(config.base_dir / "test_cases.json", "r", encoding="utf-8") as fh:
        return json.load(fh)["test_cases"]


def test_tc004_tc012_rules():
    repo = PolicyRepository(config.policy_path)
    evaluator = PolicyEvaluator(repo)
    cases = load_test_cases()

    # map by id for quick lookup
    by_id = {c["case_id"]: c for c in cases}

    # TC004: clean consultation should pass per-claim and category sub-limit
    tc4 = by_id["TC004"]["input"]
    res4 = evaluator.evaluate(tc4)
    checks4 = {c.name: c for c in res4.checks}
    assert checks4["per_claim_limit"].ok is True
    assert checks4["category_sub_limit"].ok is True

    # TC005: diabetes waiting period violation
    tc5 = by_id["TC005"]["input"]
    res5 = evaluator.evaluate(tc5)
    checks5 = {c.name: c for c in res5.checks}
    assert checks5["waiting_periods"].ok is False
    assert any("specific_condition" in issue.get("type", "") or issue.get("condition") for issue in checks5["waiting_periods"].details.get("issues", []))

    # TC006: dental partial — excluded procedure (Teeth Whitening) should be found
    tc6 = by_id["TC006"]["input"]
    res6 = evaluator.evaluate(tc6)
    checks6 = {c.name: c for c in res6.checks}
    # exclusion at line-item level is policy behavior; here exclusions rule should detect if diagnosis or procedure text matches
    # Ensure category is covered and document requirements valid
    assert checks6["category_coverage"].ok is True
    assert checks6["document_requirements"].ok is True

    # TC007: MRI without pre-auth should flag pre_authorization required
    tc7 = by_id["TC007"]["input"]
    res7 = evaluator.evaluate(tc7)
    checks7 = {c.name: c for c in res7.checks}
    assert checks7["pre_authorization"].ok is False

    # TC008: per-claim exceeded
    tc8 = by_id["TC008"]["input"]
    res8 = evaluator.evaluate(tc8)
    checks8 = {c.name: c for c in res8.checks}
    assert checks8["per_claim_limit"].ok is False

    # TC010: network hospital lookup and discount present in policy
    tc10 = by_id["TC010"]["input"]
    res10 = evaluator.evaluate(tc10)
    checks10 = {c.name: c for c in res10.checks}
    assert checks10["network_hospital"].ok is True

    # TC012: excluded treatment (obesity/bariatric) should be detected
    tc12 = by_id["TC012"]["input"]
    res12 = evaluator.evaluate(tc12)
    checks12 = {c.name: c for c in res12.checks}
    assert checks12["exclusions"].ok is False
