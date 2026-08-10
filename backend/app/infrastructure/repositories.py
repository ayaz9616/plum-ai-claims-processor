from typing import Dict, Any, List
import json
from pathlib import Path
from backend.app.schemas import PolicySnapshot
from backend.app.errors import PolicyNotFound, PolicySchemaInvalid


class PolicyRepository:
    def __init__(self, policy_path: Path):
        self.policy_path = Path(policy_path)
        self._policy = None

    def load(self) -> PolicySnapshot:
        if not self.policy_path.exists():
            raise PolicyNotFound(f"Policy file not found at {self.policy_path}")

        try:
            with open(self.policy_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception as exc:
            raise PolicyNotFound(f"Failed to read policy file: {exc}")

        # Minimal validation — ensure policy_id exists
        if "policy_id" not in raw:
            raise PolicySchemaInvalid("policy_id missing from policy file")

        # Create PolicySnapshot (keeps full raw structure in 'coverage')
        snapshot = PolicySnapshot(
            policy_id=raw.get("policy_id"),
            policy_name=raw.get("policy_name") or raw.get("policy_name"),
            insurer=raw.get("insurer"),
            coverage=raw.get("coverage"),
        )
        self._policy = raw
        return snapshot

    def raw(self):
        return self._policy


class ClaimHistoryRepository:
    def __init__(self):
        self._db = {
            "EMP008": [
                {"claim_id": "CLM_0081", "date": "2024-10-30", "amount": 1200, "provider": "City Clinic A"},
                {"claim_id": "CLM_0082", "date": "2024-10-30", "amount": 1800, "provider": "City Clinic B"},
                {"claim_id": "CLM_0083", "date": "2024-10-30", "amount": 2100, "provider": "Wellness Center"}
            ]
        }

    def get_member_claims(self, member_id: str, claim: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        # Try local seed DB first
        if member_id and member_id in self._db:
            return self._db[member_id]
            
        # Fallback to request payload
        if claim and claim.get("claims_history"):
            return claim.get("claims_history", [])
        return []
