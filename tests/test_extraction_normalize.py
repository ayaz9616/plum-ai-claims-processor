import json
from decimal import Decimal
from pathlib import Path

import pytest

from backend.config import config
from backend.extraction_normalize import (
    DocumentExtractionNormalizationError,
    normalize_money,
    normalize_structured_document_payload,
    normalize_treatment,
    parse_structured_document,
    verify_financial_consistency,
)
from backend.orchestrator import ClaimOrchestrator
from backend.policy import PolicyRepository
from backend.providers import ProviderSet, VisionResponse
from backend.trace import TraceManager
from backend.uploads import STAGING_DIR


def test_normalize_money_comma_string():
    assert normalize_money("12,000.00") == Decimal("12000.00")


def test_normalize_money_rupee_symbol():
    assert normalize_money("₹12,000.00") == Decimal("12000.00")


def test_normalize_money_integer():
    assert normalize_money(12000) == Decimal("12000")


def test_normalize_treatment_list():
    assert normalize_treatment(["Root Canal Treatment", "Teeth Whitening"]) == (
        "Root Canal Treatment; Teeth Whitening"
    )


def test_line_items_and_totals_normalize_consistently():
    payload = {
        "document_type": "HOSPITAL_BILL",
        "treatment": ["Root Canal Treatment", "Teeth Whitening"],
        "line_items": [
            {"description": "Root Canal Treatment", "amount": "₹8,000.00"},
            {"description": "Teeth Whitening", "amount": "₹4,000.00"},
        ],
        "subtotal": "12,000.00",
        "grand_total": "12,000.00",
        "amount_received": "12,000.00",
        "total": "12,000.00",
        "confidence": "0.95",
    }
    normalized, mismatches = normalize_structured_document_payload(payload)
    assert normalized["treatment"] == "Root Canal Treatment; Teeth Whitening"
    assert normalized["line_items"][0]["amount"] == Decimal("8000.00")
    assert normalized["line_items"][1]["amount"] == Decimal("4000.00")
    assert normalized["total"] == Decimal("12000.00")
    assert normalized["subtotal"] == Decimal("12000.00")
    assert normalized["grand_total"] == Decimal("12000.00")
    assert normalized["amount_received"] == Decimal("12000.00")
    assert normalized["confidence"] == Decimal("0.95")
    assert mismatches == []


def test_malformed_money_string_raises_structured_error():
    with pytest.raises(DocumentExtractionNormalizationError, match="malformed monetary value"):
        normalize_money("not-a-number", field="total")


def test_parse_structured_document_validates_normalized_payload():
    parsed, mismatches = parse_structured_document(
        {
            "document_type": "HOSPITAL_BILL",
            "line_items": [{"description": "Root Canal Treatment", "amount": 8000}],
            "total": "8,000.00",
            "confidence": 0.95,
        }
    )
    assert parsed.total == Decimal("8000.00")
    assert parsed.confidence == Decimal("0.95")
    assert mismatches == []


def test_verify_financial_consistency_detects_line_item_mismatch():
    payload, _ = normalize_structured_document_payload(
        {
            "line_items": [
                {"description": "Root Canal Treatment", "amount": 8000},
                {"description": "Teeth Whitening", "amount": 4000},
            ],
            "total": Decimal("10000.00"),
        }
    )
    mismatches = verify_financial_consistency(payload)
    assert mismatches
    assert mismatches[0]["field"] == "bill_total"


class _GeminiDentalVision:
    def analyze(self, request):
        return VisionResponse(
            text="unused",
            structured={
                "document_type": "HOSPITAL_BILL",
                "patient_name": "Priya Singh",
                "treatment_date": "2024-10-15",
                "hospital_name": "Smile Dental Clinic",
                "treatment": ["Root Canal Treatment", "Teeth Whitening"],
                "line_items": [
                    {"description": "Root Canal Treatment", "amount": "₹8,000.00"},
                    {"description": "Teeth Whitening", "amount": "₹4,000.00"},
                ],
                "subtotal": "12,000.00",
                "grand_total": "12,000.00",
                "amount_received": "12,000.00",
                "total": "12,000.00",
                "quality": "GOOD",
                "confidence": "0.95",
            },
            metadata={"model": "fake-gemini"},
        )


def _orchestrator(providers=None):
    return ClaimOrchestrator(PolicyRepository(config.policy_path), TraceManager(), providers)


def _case(case_id):
    data = json.loads((config.base_dir / "test_cases.json").read_text(encoding="utf-8"))
    return next(case["input"] for case in data["test_cases"] if case["case_id"] == case_id)


def test_gemini_dental_bill_normalization_produces_partial_decision():
    document_id = "tc006-gemini-dental.jpg"
    staged = STAGING_DIR / document_id
    staged.write_bytes(b"fake-image")
    claim = {
        "member_id": "EMP002",
        "policy_id": "PLUM_GHI_2024",
        "claim_category": "DENTAL",
        "treatment_date": "2024-10-15",
        "claimed_amount": 12000,
        "documents": [{"file_id": document_id, "file_name": "bill.jpg", "mime_type": "image/jpeg"}],
    }
    try:
        result = _orchestrator(ProviderSet(vision=_GeminiDentalVision())).process_claim(claim)
    finally:
        staged.unlink(missing_ok=True)

    extraction = next(event for event in result.trace if event.step == "DOCUMENT_EXTRACTION")
    assert extraction.status == "OK"
    assert not any(item.get("component") == "DocumentExtraction" for item in result.component_failures)
    assert result.decision == "PARTIAL"
    assert result.approved_amount == Decimal("8000.00")


def test_tc006_fixture_partial_approval():
    result = _orchestrator().process_claim(_case("TC006"))
    assert result.decision == "PARTIAL"
    assert result.approved_amount == Decimal("8000.00")
    assert not any(item.get("component") == "DocumentExtraction" for item in result.component_failures)
