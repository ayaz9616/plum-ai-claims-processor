import json
from pathlib import Path

from backend.config import config
from backend.orchestrator import ClaimOrchestrator
from backend.policy import PolicyRepository
from backend.providers import ProviderSet, VisionResponse
from backend.trace import TraceManager
from backend.uploads import STAGING_DIR


def _orchestrator(providers=None):
    return ClaimOrchestrator(PolicyRepository(config.policy_path), TraceManager(), providers)


def _case(case_id):
    data = json.loads((config.base_dir / "test_cases.json").read_text(encoding="utf-8"))
    return next(case["input"] for case in data["test_cases"] if case["case_id"] == case_id)


def test_member_with_dependents_is_structured_and_valid():
    orchestrator = _orchestrator()
    orchestrator.policy_repo.load()
    result = orchestrator.workflow.member_resolver.resolve(_case("TC004"), orchestrator.policy_repo.raw())
    assert result.eligible
    assert result.dependents == [
        {"dependent_id": "DEP001", "name": "Sunita Kumar", "relationship": "SPOUSE", "primary_member_id": "EMP001"},
        {"dependent_id": "DEP002", "name": "Arjun Kumar", "relationship": "CHILD", "primary_member_id": "EMP001"},
    ]


def test_member_document_mismatch_blocks_before_adjudication():
    result = _orchestrator().process_claim(_case("TC003"))
    steps = [event.step for event in result.trace]
    assert result.decision is None
    assert result.processing_status == "BLOCKED"
    assert result.reason_code == "DOCUMENT_VERIFICATION_FAILED"
    skipped = {event.step: event for event in result.trace if event.status == "SKIPPED"}
    assert skipped["POLICY_EVALUATION"].reason_code == "UPSTREAM_STAGE_FAILED"
    assert skipped["FINANCIAL_CALCULATION"].reason_code == "UPSTREAM_STAGE_FAILED"


def test_unrelated_dependent_is_not_accepted_for_employee():
    claim = _case("TC004")
    claim["member_id"] = "EMP002"
    claim["documents"][0]["content"]["patient_name"] = "Sunita Kumar"
    claim["documents"][1]["content"]["patient_name"] = "Sunita Kumar"
    result = _orchestrator().process_claim(claim)
    assert result.decision is None
    assert result.processing_status == "BLOCKED"


def test_valid_dependent_can_be_claimed_directly():
    claim = _case("TC004")
    claim["member_id"] = "DEP001"
    claim["documents"][0]["content"]["patient_name"] = "Sunita Kumar"
    claim["documents"][1]["content"]["patient_name"] = "Sunita Kumar"
    result = _orchestrator().process_claim(claim)
    assert result.processing_status == "COMPLETED"
    assert result.decision == "APPROVED"


def test_cross_document_date_and_bill_total_mismatches_gate_adjudication():
    claim = _case("TC004")
    claim["member_id"] = "EMP002"
    for document in claim["documents"]:
        document["content"]["patient_name"] = "Priya Singh"
    claim["documents"][0]["content"]["date"] = "2024-11-01"
    claim["documents"][1]["content"]["date"] = "2024-11-02"
    claim["documents"][1]["content"]["total"] = 1600
    result = _orchestrator().process_claim(claim)
    consistency = next(event.safe_output for event in result.trace if event.step == "CROSS_DOCUMENT_CONSISTENCY")
    assert result.processing_status == "BLOCKED"
    assert {item["field"] for item in consistency["mismatches"]} == {"treatment_date", "bill_total"}
    assert next(event for event in result.trace if event.step == "POLICY_EVALUATION").status == "SKIPPED"


class _FakeVision:
    def analyze(self, request):
        return VisionResponse(
            text=json.dumps({"document_type": "PRESCRIPTION", "patient_name": "Priya Singh", "treatment_date": "2024-10-15", "quality": "GOOD", "confidence": "0.98"}),
            structured={}, metadata={"model": "fake-gemini"},
        )


def test_uploaded_document_is_extracted_by_backend_before_workflow():
    document_id = "p0-production-test.jpg"
    staged = STAGING_DIR / document_id
    staged.write_bytes(b"fake-image")
    claim = {
        "member_id": "EMP002", "policy_id": "PLUM_GHI_2024", "claim_category": "DENTAL",
        "treatment_date": "2024-10-15", "claimed_amount": 1000,
        "documents": [{"file_id": document_id, "file_name": "receipt.jpg", "mime_type": "image/jpeg"}],
    }
    try:
        result = _orchestrator(ProviderSet(vision=_FakeVision())).process_claim(claim)
    finally:
        staged.unlink(missing_ok=True)
    extraction = next(event for event in result.trace if event.step == "DOCUMENT_EXTRACTION")
    assert extraction.safe_output[0]["extracted"]["patient_name"] == "Priya Singh"
    assert extraction.safe_output[0]["document_type"] == "PRESCRIPTION"
