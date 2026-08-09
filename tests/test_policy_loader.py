from backend.policy import PolicyRepository
from backend.config import config


def test_policy_loads():
    repo = PolicyRepository(config.policy_path)
    policy = repo.load()
    assert policy.policy_id == "PLUM_GHI_2024"
