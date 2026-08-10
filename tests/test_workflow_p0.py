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


def test_final_decision_summaries_explain_official_outcomes():
    expectations = {
        "TC004": ("APPROVED", "₹1,350", "prescription and hospital bill"),
        "TC006": ("PARTIAL", "Root Canal Treatment", "Teeth Whitening"),
        "TC007": ("REJECTED", "pre-authorization", "MRI"),
        "TC009": ("MANUAL_REVIEW", "4 claims", "same day"),
        "TC011": ("APPROVED", "FraudAnalyzer", "manual review is recommended"),
    }
    for case_id, phrases in expectations.items():
        result = _orchestrator().process_claim(_case(case_id))
        assert result.decision == phrases[0]
        assert result.decision_summary
        assert "\n" not in result.decision_summary
        for phrase in phrases[1:]:
            assert phrase.lower() in result.decision_summary.lower()


def test_document_blocks_have_actionable_decision_summary():
    for case_id in ("TC001", "TC002"):
        result = _orchestrator().process_claim(_case(case_id))
        assert result.decision is None
        assert "please re-upload" in result.decision_summary.lower()
        assert result.decision_summary.endswith(".")


def test_pharmacy_bill_with_unreadable_critical_fields_is_blocked_before_adjudication():
    claim = _case("TC002")
    claim["documents"][1].pop("quality")
    claim["documents"][1]["content"] = {
        "patient_name": "Sneha Reddy", "hospital_name": "Health First Pharmacy",
        "line_items": [{"description": "Paracetamol 500mg", "amount": None}],
    }
    result = _orchestrator().process_claim(claim)
    quality = next(event for event in result.trace if event.step == "DOCUMENT_QUALITY")
    assert result.decision is None
    assert result.processing_status == "BLOCKED"
    assert quality.status == "NEEDS_REUPLOAD"
    assert quality.safe_output["unreadable"][0]["document_type"] == "PHARMACY_BILL"
    assert {"bill_date", "line_item_amounts", "total_amount"} <= set(quality.safe_output["unreadable"][0]["missing_or_unreliable_fields"])
    assert "pharmacy bill" in result.decision_summary.lower()
    assert next(event for event in result.trace if event.step == "POLICY_EVALUATION").status == "SKIPPED"


def test_readable_pharmacy_bill_passes_deterministic_quality_gate():
    claim = _case("TC002")
    claim["documents"][1].pop("quality")
    claim["documents"][1]["content"] = {
        "patient_name": "Sneha Reddy", "date": "2024-10-25", "hospital_name": "Health First Pharmacy",
        "line_items": [{"description": "Paracetamol", "amount": 800}], "total": 800,
    }
    result = _orchestrator().process_claim(claim)
    quality = next(event for event in result.trace if event.step == "DOCUMENT_QUALITY")
    assert quality.status == "OK"
    assert result.decision is not None


class _EmptyVision:
    def analyze(self, request):
        return VisionResponse(text="", structured={}, metadata={"model": "fake-gemini"})


class _StructuredVision:
    def analyze(self, request):
        return VisionResponse(
            text="not json", structured={"document_type": "PRESCRIPTION", "patient_name": "Priya Singh", "quality": "GOOD"}, metadata={"model": "fake-gemini"}
        )


def test_invalid_upload_response_blocks_once_without_overwriting_successful_extraction():
    document_id = "empty-vision.jpg"
    staged = STAGING_DIR / document_id
    staged.write_bytes(b"fake-image")
    claim = {"member_id": "EMP002", "policy_id": "PLUM_GHI_2024", "claim_category": "DENTAL", "treatment_date": "2024-10-15", "claimed_amount": 1000, "documents": [{"file_id": document_id, "mime_type": "image/jpeg"}]}
    try:
        result = _orchestrator(ProviderSet(vision=_EmptyVision())).process_claim(claim)
    finally:
        staged.unlink(missing_ok=True)
    extraction_events = [event for event in result.trace if event.step == "DOCUMENT_EXTRACTION"]
    assert len(extraction_events) == 1
    assert extraction_events[0].status == "ERROR"
    assert "could not be successfully extracted" in result.decision_summary


def test_provider_structured_output_is_validated_before_text_fallback():
    document_id = "structured-vision.jpg"
    staged = STAGING_DIR / document_id
    staged.write_bytes(b"fake-image")
    claim = {"member_id": "EMP002", "policy_id": "PLUM_GHI_2024", "claim_category": "DENTAL", "treatment_date": "2024-10-15", "claimed_amount": 1000, "documents": [{"file_id": document_id, "mime_type": "image/jpeg"}]}
    try:
        result = _orchestrator(ProviderSet(vision=_StructuredVision())).process_claim(claim)
    finally:
        staged.unlink(missing_ok=True)
    extraction = next(event for event in result.trace if event.step == "DOCUMENT_EXTRACTION")
    assert extraction.status == "OK"
    assert extraction.safe_output[0]["document_type"] == "PRESCRIPTION"


def test_identity_consistency_normalizes_safe_ocr_format_variations():
    claim = _case("TC004")
    claim["documents"][0]["content"]["patient_name"] = "RAJESH KUMAR."
    claim["documents"][1]["content"]["patient_name"] = "Rajesh  Kumar "
    result = _orchestrator().process_claim(claim)
    assert result.decision == "APPROVED"
    assert next(event for event in result.trace if event.step == "CROSS_DOCUMENT_CONSISTENCY").status == "PASSED"


def test_conflicting_bill_totals_continue_to_calculation_and_manual_review():
    claim = _case("TC004")
    claim["claimed_amount"] = 1575
    bill = claim["documents"][1]["content"]
    bill.update({"total": 1750, "grand_total": 1750, "amount_payable": 1575})
    result = _orchestrator().process_claim(claim)
    consistency = next(event for event in result.trace if event.step == "CROSS_DOCUMENT_CONSISTENCY")
    assert result.decision == "MANUAL_REVIEW"
    assert consistency.status == "REVIEW_REQUIRED"
    assert next(event for event in result.trace if event.step == "POLICY_EVALUATION").status == "OK"
    assert next(event for event in result.trace if event.step == "FINANCIAL_CALCULATION").status == "OK"
    assert next(event for event in result.trace if event.step == "CONFIDENCE").status == "OK"
    assert result.reimbursable_amount == 1417.5
    assert "conflicting totals" in result.decision_summary
