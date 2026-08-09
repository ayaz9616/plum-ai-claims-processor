import json
from pathlib import Path
from .schemas import PolicySnapshot
from .errors import PolicyNotFound, PolicySchemaInvalid


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
