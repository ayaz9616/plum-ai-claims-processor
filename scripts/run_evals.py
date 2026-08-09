import os
import json
import sys
from pathlib import Path

# Clear DATABASE_URL so evals run without requiring psycopg
os.environ["DATABASE_URL"] = ""

# ensure repo root on path
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


def run():
    repo = PolicyRepository(config.policy_path)
    trace = TraceManager()
    orch = ClaimOrchestrator(repo, trace)
    cases = load_cases()
    results = []
    for c in cases:
        inp = c["input"]
        expected = c.get("expected", {})
        try:
            out = orch.process_claim(inp)
            res = {
                "case_id": c["case_id"],
                "expected": expected,
                "actual": {
                    "decision": out.decision,
                    "approved_amount": str(out.approved_amount) if out.approved_amount is not None else None,
                    "confidence_score": str(out.confidence_score) if out.confidence_score is not None else None,
                },
                "trace_events": [te.model_dump(mode="python") for te in out.trace],
            }
        except Exception as exc:
            res = {"case_id": c["case_id"], "error": str(exc)}
        results.append(res)

    # Compare expected vs actual pass/fail (simple checks)
    summary = []
    for r in results:
        cid = r["case_id"]
        expected = r.get("expected")
        actual = r.get("actual")
        if not expected or not actual:
            status = "ERROR"
        else:
            exp_dec = expected.get("decision")
            act_dec = actual.get("decision")
            pass_dec = (exp_dec == act_dec)
            # check approved amount if provided in expected
            exp_amt = expected.get("approved_amount")
            act_amt = actual.get("approved_amount")
            pass_amt = True
            if exp_amt is not None:
                pass_amt = (str(exp_amt) == str(act_amt))
            status = "PASS" if (pass_dec and pass_amt) else "FAIL"
        summary.append({"case_id": cid, "status": status, "expected": expected, "actual": actual})

    print("Evaluation Summary:")
    for s in summary:
        print(f"{s['case_id']}: {s['status']}")

    # write results
    with open(config.base_dir / "eval_results.json", "w", encoding="utf-8") as fh:
        json.dump({"results": results, "summary": summary}, fh, indent=2, default=str)

    return summary


if __name__ == "__main__":
    run()
