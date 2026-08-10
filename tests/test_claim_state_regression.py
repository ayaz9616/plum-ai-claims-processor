import json
from pathlib import Path

from backend.app.config import config
from backend.orchestrator import ClaimOrchestrator
from backend.app.infrastructure.repositories import PolicyRepository
from backend.app.core.policy import PolicyEvaluator
from backend.app.trace import TraceManager


def _case(case_id: str):
    data = json.loads((config.base_dir / "test_cases.json").read_text(encoding="utf-8"))
    return next(case["input"] for case in data["test_cases"] if case["case_id"] == case_id)


def _orchestrator():
    return ClaimOrchestrator(PolicyRepository(config.policy_path), TraceManager())


def test_consecutive_claims_do_not_share_member_identity():
    orchestrator = _orchestrator()
    tc4 = orchestrator.process_claim(_case("TC004"))
    tc5 = orchestrator.process_claim(_case("TC005"))
    tc6 = orchestrator.process_claim(_case("TC006"))

    def member_name(result):
        trace = next(event for event in result.trace if event.step == "MEMBER_RESOLUTION")
        return trace.safe_output["member_name"], trace.safe_output["member_id"]

    assert member_name(tc4) == ("Rajesh Kumar", "EMP001")
    assert member_name(tc5) == ("Vikram Joshi", "EMP005")
    assert member_name(tc6) == ("Priya Singh", "EMP002")
    assert tc4.claim_id != tc5.claim_id != tc6.claim_id


def test_identity_consistency_treats_case_variations_as_match():
    claim = _case("TC005")
    claim["documents"][0]["content"]["patient_name"] = "VIKRAM JOSHI"
    claim["documents"][1]["content"]["patient_name"] = "Vikram Joshi"
    evaluation = PolicyEvaluator(PolicyRepository(config.policy_path)).evaluate(claim)
    identity = next(check for check in evaluation.checks if check.name == "identity_consistency")
    assert identity.ok is True


def test_tc006_financial_trace_contains_dental_line_items():
    result = _orchestrator().process_claim(_case("TC006"))
    finance = next(event for event in result.trace if event.step == "FINANCIAL_CALCULATION")
    line_items = finance.safe_output["breakdown"]["line_items"]
    assert result.decision == "PARTIAL"
    assert result.approved_amount == 8000
    assert len(line_items) == 2
    assert any(item["description"] == "Root Canal Treatment" and item["eligible"] is True for item in line_items)
    assert any(item["description"] == "Teeth Whitening" and item["eligible"] is False for item in line_items)
