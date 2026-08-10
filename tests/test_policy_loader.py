from backend.app.infrastructure.repositories import PolicyRepository
from backend.app.config import config


def test_policy_loads():
    repo = PolicyRepository(config.policy_path)
    policy = repo.load()
    assert policy.policy_id == "PLUM_GHI_2024"
