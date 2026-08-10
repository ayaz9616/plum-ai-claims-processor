import os
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Clear DATABASE_URL so evals run without requiring psycopg
os.environ["DATABASE_URL"] = ""

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.policy import PolicyRepository
from backend.orchestrator import ClaimOrchestrator
from backend.trace import TraceManager
from backend.config import config


def load_cases():
    with open(config.base_dir / "test_cases.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["test_cases"]


def _trace_blob(trace_events: List[Dict[str, Any]]) -> str:
    return json.dumps(trace_events, default=str).lower()


def _check_confidence(expected: str, actual: Any) -> Tuple[bool, str]:
    if actual is None:
        return False, "confidence_score missing"
    value = float(actual)
    if expected == "above 0.85":
        return value > 0.85, f"confidence {value} is not above 0.85"
    if expected == "above 0.90":
        return value > 0.90, f"confidence {value} is not above 0.90"
    return True, ""


def _validate_system_must(case_id: str, must: str, out, trace_events: List[Dict[str, Any]]) -> Tuple[bool, str]:
    summary = (out.decision_summary or "").lower()
    trace_text = _trace_blob(trace_events)
    combined = f"{summary} {trace_text}"
    must_lower = must.lower()

    if "stop before making any claim decision" in must_lower:
        if out.decision is not None:
            return False, "expected no decision before blocking"
        return True, ""

    if "tell the member specifically what document type was uploaded" in must_lower:
        if not any(token in combined for token in ("prescription", "hospital_bill", "uploaded")):
            return False, "blocked message did not name uploaded/required document types"
        return True, ""

    if "not return a generic error" in must_lower:
        if "error" in summary and "uploaded" not in summary and "required" not in summary:
            return False, "blocked message appears too generic"
        return True, ""

    if "pharmacy bill cannot be read" in must_lower or "identify that the pharmacy bill cannot be read" in must_lower:
        if "pharmacy" not in combined or "re-upload" not in combined:
            return False, "did not identify unreadable pharmacy bill"
        return True, ""

    if "ask the member to re-upload that specific document" in must_lower:
        if "re-upload" not in combined:
            return False, "did not ask member to re-upload"
        return True, ""

    if "not reject the claim outright" in must_lower:
        if out.decision in {"REJECTED", "PARTIAL", "APPROVED"}:
            return False, "unreadable document incorrectly produced a claim decision"
        return True, ""

    if "documents belong to different people" in must_lower or "surface this to the member with the specific names" in must_lower:
        if not all(name in combined for name in ("rajesh", "arjun")):
            return False, "did not surface both patient names"
        return True, ""

    if "not proceed to a claim decision" in must_lower:
        if out.decision is not None:
            return False, "proceeded to a claim decision after identity mismatch"
        return True, ""

    if "state the date from which the member will be eligible" in must_lower:
        if not any(token in combined for token in ("2024-11-30", "30 november 2024", "november 2024")):
            return False, "waiting-period message did not include eligibility date"
        return True, ""

    if "itemize which line items were approved" in must_lower:
        if "root canal" not in combined or "teeth whitening" not in combined:
            return False, "partial approval did not itemize covered and excluded line items"
        return True, ""

    if "reason for each rejection at the line-item level" in must_lower:
        if "cosmetic" not in combined and "excluded" not in combined and "policy exclusion" not in combined:
            return False, "partial approval did not explain line-item rejection reason"
        return True, ""

    if "pre-authorization was required and not obtained" in must_lower:
        if "pre-authorization" not in combined and "pre authorization" not in combined:
            return False, "did not explain missing pre-authorization"
        return True, ""

    if "resubmit with pre-auth" in must_lower or "resubmit the claim" in must_lower:
        if "resubmit" not in combined:
            return False, "did not provide pre-authorization resubmission guidance"
        return True, ""

    if "per-claim limit" in must_lower and "claimed amount" in must_lower:
        if "per-claim limit" not in summary and "per claim limit" not in summary:
            return False, "rejection did not state per-claim limit clearly"
        if str(out.claim_id) and "7500" not in combined and "7,500" not in combined:
            # TC008 only
            if case_id == "TC008" and "7500" not in summary.replace(",", "") and "7,500" not in summary:
                return False, "rejection did not state claimed amount clearly"
        return True, ""

    if "flag the unusual same-day claim pattern" in must_lower:
        if "same day" not in combined and "same-day" not in combined:
            return False, "manual review did not flag same-day pattern"
        return True, ""

    if "route to manual review rather than auto-rejecting" in must_lower:
        if out.decision != "MANUAL_REVIEW":
            return False, "expected MANUAL_REVIEW instead of auto-reject"
        return True, ""

    if "specific signals that triggered the flag" in must_lower:
        if "4 claims" not in combined and '"count"' not in combined:
            return False, "manual review did not include fraud signal details"
        return True, ""

    if "network discount before co-pay" in must_lower:
        financial = next((event for event in trace_events if event.get("step") == "FINANCIAL_CALCULATION"), None)
        breakdown = ((financial or {}).get("safe_output") or {}).get("breakdown") or {}
        if not breakdown.get("network_applied"):
            return False, "network discount was not applied"
        return True, ""

    if "breakdown of discount and co-pay" in must_lower:
        if "co-pay" not in summary and "copay" not in summary:
            return False, "approval did not show co-pay breakdown"
        financial = next((event for event in trace_events if event.get("step") == "FINANCIAL_CALCULATION"), None)
        breakdown = ((financial or {}).get("safe_output") or {}).get("breakdown") or {}
        if breakdown.get("network_discount") in (None, "0", 0):
            return False, "approval did not show network discount breakdown"
        return True, ""

    if "not crash or return a 500 error" in must_lower:
        return True, ""

    if "component failed and was skipped" in must_lower or "indicate in the output that a component failed" in must_lower:
        if not out.degraded and not out.component_failures:
            return False, "degraded component failure was not surfaced"
        return True, ""

    if "confidence score lower than a normal full-pipeline approval" in must_lower:
        if out.confidence_score is None or float(out.confidence_score) >= 0.85:
            return False, "degraded approval confidence was not reduced enough"
        return True, ""

    if "manual review is recommended due to incomplete processing" in must_lower:
        if not out.manual_review_recommended and "manual review" not in summary:
            return False, "degraded approval did not recommend manual review"
        return True, ""

    return True, f"no validator implemented for system_must: {must}"


def validate_case(case: Dict[str, Any], out) -> List[str]:
    failures: List[str] = []
    expected = case.get("expected", {})
    trace_events = [event.model_dump(mode="python") for event in out.trace]
    summary = (out.decision_summary or "").lower()

    if out.decision != expected.get("decision"):
        failures.append(f"decision expected {expected.get('decision')}, got {out.decision}")

    if expected.get("approved_amount") is not None:
        actual_amount = str(out.approved_amount) if out.approved_amount is not None else None
        if str(expected["approved_amount"]) != actual_amount:
            failures.append(f"approved_amount expected {expected['approved_amount']}, got {actual_amount}")

    if expected.get("decision") is None:
        if out.processing_status != "BLOCKED":
            failures.append(f"expected processing_status BLOCKED, got {out.processing_status}")
        if out.decision is not None:
            failures.append("blocked case returned a decision")

    for rejection_reason in expected.get("rejection_reasons", []):
        actual_reason = str(out.reason or "").upper()
        decision_output = next(
            (event.get("safe_output") or {} for event in reversed(trace_events) if event.get("step") == "DECISION"),
            {},
        )
        trace_reason = str(decision_output.get("reason") or "").upper()
        if rejection_reason not in {actual_reason, trace_reason}:
            failures.append(f"rejection_reason expected {rejection_reason}, got {actual_reason or trace_reason}")

    if expected.get("confidence_score"):
        ok, message = _check_confidence(expected["confidence_score"], out.confidence_score)
        if not ok:
            failures.append(message)

    if case["case_id"] == "TC012":
        if "excluded" not in summary and "obesity" not in summary and "bariatric" not in summary and "weight loss" not in summary:
            failures.append("TC012 summary did not explain excluded obesity/bariatric treatment")
        if "per-claim limit" in summary or "per claim limit" in summary:
            failures.append("TC012 summary incorrectly referenced per-claim limit")

    if case["case_id"] == "TC005":
        if not any(token in summary for token in ("30 november 2024", "november 2024", "2024-11-30")):
            failures.append("TC005 summary did not include diabetes eligibility date")

    if case["case_id"] == "TC007":
        if "resubmit" not in summary:
            failures.append("TC007 summary did not include pre-authorization resubmission guidance")

    for must in expected.get("system_must", []):
        ok, message = _validate_system_must(case["case_id"], must, out, trace_events)
        if not ok:
            failures.append(message)

    completed_steps = {event.get("step") for event in trace_events}
    if case["case_id"] == "TC001" and "POLICY_EVALUATION" in completed_steps and any(
        event.get("step") == "POLICY_EVALUATION" and event.get("status") != "SKIPPED" for event in trace_events
    ):
        failures.append("TC001 proceeded to policy evaluation instead of stopping early")

    if case["case_id"] in {"TC001", "TC002", "TC003"}:
        extraction_events = [event for event in trace_events if event.get("step") == "DOCUMENT_EXTRACTION"]
        if extraction_events and case["case_id"] in {"TC001", "TC002"}:
            if case["case_id"] == "TC001" and any(event.get("status") == "OK" for event in extraction_events):
                failures.append("TC001 should block before document extraction completes")

    if case["case_id"] == "TC011":
        if not out.component_failures:
            failures.append("TC011 did not record component_failures")
        if not out.degraded:
            failures.append("TC011 did not mark output as degraded")

    verification_index = next((index for index, event in enumerate(trace_events) if event.get("step") == "DOCUMENT_VERIFICATION"), None)
    extraction_index = next((index for index, event in enumerate(trace_events) if event.get("step") == "DOCUMENT_EXTRACTION"), None)
    if verification_index is not None and extraction_index is not None and verification_index > extraction_index:
        failures.append("pipeline ran document extraction before required-document verification")

    return failures


def run():
    repo = PolicyRepository(config.policy_path)
    trace = TraceManager()
    orch = ClaimOrchestrator(repo, trace)
    cases = load_cases()
    results = []
    summary = []

    for case in cases:
        expected = case.get("expected", {})
        try:
            out = orch.process_claim(case["input"])
            trace_events = [event.model_dump(mode="python") for event in out.trace]
            failures = validate_case(case, out)
            actual = {
                "decision": out.decision,
                "approved_amount": str(out.approved_amount) if out.approved_amount is not None else None,
                "confidence_score": str(out.confidence_score) if out.confidence_score is not None else None,
                "processing_status": out.processing_status,
                "reason": out.reason,
                "reason_code": out.reason_code,
                "decision_summary": out.decision_summary,
                "degraded": out.degraded,
                "manual_review_recommended": out.manual_review_recommended,
                "component_failures": out.component_failures,
            }
            results.append(
                {
                    "case_id": case["case_id"],
                    "expected": expected,
                    "actual": actual,
                    "validation_failures": failures,
                    "trace_events": trace_events,
                }
            )
            summary.append(
                {
                    "case_id": case["case_id"],
                    "status": "PASS" if not failures else "FAIL",
                    "failures": failures,
                    "expected": expected,
                    "actual": actual,
                }
            )
        except Exception as exc:
            results.append({"case_id": case["case_id"], "error": str(exc)})
            summary.append({"case_id": case["case_id"], "status": "ERROR", "error": str(exc)})

    print("Evaluation Summary:")
    for item in summary:
        if item["status"] == "PASS":
            print(f"{item['case_id']}: PASS")
        else:
            print(f"{item['case_id']}: {item['status']}")
            for failure in item.get("failures", []):
                print(f"  - {failure}")
            if item.get("error"):
                print(f"  - {item['error']}")

    with open(config.base_dir / "eval_results.json", "w", encoding="utf-8") as fh:
        json.dump({"results": results, "summary": summary}, fh, indent=2, default=str)

    return summary


if __name__ == "__main__":
    run()
