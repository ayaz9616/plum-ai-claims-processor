from fastapi import FastAPI
from .policy import PolicyRepository
from .trace import TraceManager
from .orchestrator import ClaimOrchestrator
from .config import config
from .providers import build_provider_set

app = FastAPI(title="Plum Claims - Backend")


@app.get("/health")
def health():
    return {"status": "ok"}


# instantiate core components for wiring tests
policy_repo = PolicyRepository(config.policy_path)
trace_manager = TraceManager()
orchestrator = ClaimOrchestrator(policy_repo, trace_manager)
provider_set = build_provider_set()
