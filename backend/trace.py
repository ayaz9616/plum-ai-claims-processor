from typing import List
from .schemas import TraceEvent
import threading


class TraceManager:
    def __init__(self):
        self._events: List[TraceEvent] = []
        self._lock = threading.Lock()

    def add_event(self, event: TraceEvent):
        with self._lock:
            self._events.append(event)

    def get_events_for_claim(self, claim_id: str) -> List[TraceEvent]:
        with self._lock:
            return [e for e in self._events if e.claim_id == claim_id]
