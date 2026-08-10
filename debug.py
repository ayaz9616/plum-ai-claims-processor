import sys
from backend.main import orchestrator
from tests.conftest import _case

result = orchestrator.process_claim(_case("TC006"))
for evt in result.trace:
    print(f"{evt.step} - {evt.status} - {evt.error}")
print(f"Decision: {result.decision}")
