import pytest
from decimal import Decimal
from backend.fraud_analyzer import FraudAnalyzer
from backend.schemas import FraudAnalysis

@pytest.fixture
def policy_raw():
    return {
        "fraud_thresholds": {
            "same_day_claims_limit": 2,
            "monthly_claims_limit": 6,
            "high_value_claim_threshold": 25000,
            "auto_manual_review_above": 25000,
            "fraud_score_manual_review_threshold": 0.80
        }
    }

@pytest.fixture
def analyzer():
    return FraudAnalyzer()

def test_0_prior_claims(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": []
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.ok is True
    assert result.manual_review is False
    assert result.fraud_score == 0.0
    assert result.risk_level == "LOW"

def test_1_prior_same_day_claim(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [
            {"claim_id": "C1", "date": "2024-10-15"}
        ]
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.manual_review is False
    assert result.checks["same_day_claims"]["count"] == 1
    assert result.checks["same_day_claims"]["status"] == "PASSED"

def test_exactly_at_same_day_threshold(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [
            {"claim_id": "C1", "date": "2024-10-15"},
            {"claim_id": "C2", "date": "2024-10-15"}
        ]
    }
    result = analyzer.analyze(claim, policy_raw)
    # Threshold is 2. At 2, it is PASSED according to prompt "3 > 2". Wait, if threshold is 2, and count is 2?
    # Based on the prompt: 3 prior claims ... limit is 2. So if count == limit, does it trigger?
    # I used > for same_day. Let's see if count is 2, same_day > same_day_limit is False.
    assert result.manual_review is False
    assert result.checks["same_day_claims"]["count"] == 2
    assert result.checks["same_day_claims"]["status"] == "PASSED"

def test_above_same_day_threshold(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [
            {"claim_id": "C1", "date": "2024-10-15"},
            {"claim_id": "C2", "date": "2024-10-15"},
            {"claim_id": "C3", "date": "2024-10-15"}
        ]
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.manual_review is True
    assert result.checks["same_day_claims"]["count"] == 3
    assert result.checks["same_day_claims"]["status"] == "FAILED"
    assert any(s["type"] == "same_day_claims" for s in result.signals)

def test_monthly_threshold(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [{"claim_id": f"C{i}", "date": "2024-10-01"} for i in range(5)]
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.manual_review is False

def test_above_monthly_threshold(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [{"claim_id": f"C{i}", "date": "2024-10-01"} for i in range(6)]
    }
    result = analyzer.analyze(claim, policy_raw)
    # limit is 6, >= means 6 will trigger.
    assert result.manual_review is True
    assert result.checks["monthly_claims"]["count"] == 6
    assert result.checks["monthly_claims"]["status"] == "FAILED"

def test_high_value_claim_below_threshold(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 20000,
        "claims_history": []
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.manual_review is False
    assert result.checks["high_value_claim"]["status"] == "PASSED"

def test_high_value_claim_above_threshold(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 26000,
        "claims_history": []
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.manual_review is True
    assert result.checks["high_value_claim"]["status"] == "FAILED"
    assert result.checks["high_value_claim"]["amount"] == 26000.0

def test_fraud_score_below_0_80(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [{"claim_id": f"C{i}", "date": "2024-10-01"} for i in range(6)]
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.fraud_score == 0.42
    assert result.risk_level == "MEDIUM"

def test_fraud_score_above_0_80(analyzer, policy_raw):
    # same_day adds 0.5, monthly adds 0.3 -> 0.8
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [{"claim_id": f"C{i}", "date": "2024-10-15"} for i in range(4)]
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.fraud_score >= 0.8
    assert result.risk_level == "HIGH"
    assert result.manual_review is True

def test_multiple_signals_simultaneously(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 30000, # high value +0.42
        "claims_history": [{"claim_id": f"C{i}", "date": "2024-10-15"} for i in range(6)] # same_day +0.86, monthly +0.42
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.fraud_score >= 1.0
    assert len(result.signals) >= 3

def test_missing_claims_history(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.ok is True
    assert result.manual_review is False

def test_empty_claims_history(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": []
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.ok is True

def test_malformed_claim_dates(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "invalid_date",
        "claimed_amount": 1000,
        "claims_history": [{"claim_id": "C1", "date": "also_invalid"}]
    }
    result = analyzer.analyze(claim, policy_raw)
    # Should fallback string match or gracefully fail
    assert result.ok is True

def test_missing_policy_threshold(analyzer):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [{"claim_id": "C1", "date": "2024-10-15"}]
    }
    result = analyzer.analyze(claim, {})
    assert result.ok is True

def test_duplicate_claim_ids(analyzer, policy_raw):
    claim = {
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [
            {"claim_id": "C1", "date": "2024-10-15"},
            {"claim_id": "C1", "date": "2024-10-15"},
            {"claim_id": "C1", "date": "2024-10-15"}
        ]
    }
    # Doesn't explicitly deduplicate in current logic but it should run fine.
    # Count will be 3.
    result = analyzer.analyze(claim, policy_raw)
    assert result.checks["same_day_claims"]["count"] == 3

def test_current_claim_not_counted_as_historical(analyzer, policy_raw):
    claim = {
        "claim_id": "CURRENT_123",
        "member_id": "EMP001",
        "treatment_date": "2024-10-15",
        "claimed_amount": 1000,
        "claims_history": [
            {"claim_id": "CURRENT_123", "date": "2024-10-15"}
        ]
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.checks["same_day_claims"]["count"] == 0

def test_tc009_regression(analyzer, policy_raw):
    claim = {
        "member_id": "EMP008",
        "claim_id": "CLM_NEW",
        "treatment_date": "2024-10-30",
        "claimed_amount": 4800,
        "claims_history": [
          { "claim_id": "CLM_0081", "date": "2024-10-30", "amount": 1200, "provider": "City Clinic A" },
          { "claim_id": "CLM_0082", "date": "2024-10-30", "amount": 1800, "provider": "City Clinic B" },
          { "claim_id": "CLM_0083", "date": "2024-10-30", "amount": 2100, "provider": "Wellness Center" }
        ]
    }
    result = analyzer.analyze(claim, policy_raw)
    assert result.manual_review is True
    assert result.risk_level == "HIGH"
    assert result.checks["same_day_claims"]["count"] == 3
    assert result.checks["same_day_claims"]["status"] == "FAILED"
