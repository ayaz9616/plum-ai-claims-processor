from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterator, Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional dependency
    psycopg = None
    dict_row = None


def _json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return _json_ready(asdict(value))
    if hasattr(value, "model_dump"):
        return _json_ready(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class ClaimAuditRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url.strip()

    @property
    def enabled(self) -> bool:
        return bool(self.database_url)

    def initialize(self) -> None:
        if not self.enabled:
            return
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS claim_audit_events (
                        id BIGSERIAL PRIMARY KEY,
                        claim_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS claim_results (
                        claim_id TEXT PRIMARY KEY,
                        member_id TEXT NOT NULL,
                        policy_id TEXT NOT NULL,
                        decision TEXT,
                        approved_amount NUMERIC,
                        confidence_score NUMERIC,
                        processing_status TEXT NOT NULL,
                        degraded BOOLEAN NOT NULL,
                        claim_context JSONB NOT NULL,
                        policy_evaluation JSONB,
                        financial_calculation JSONB,
                        fraud_analysis JSONB,
                        trace JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            connection.commit()

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        if not self.enabled:
            raise RuntimeError("database_url is not configured")
        if psycopg is None:
            raise RuntimeError("psycopg is not installed")
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def persist_claim_bundle(self, claim_id: str, raw_claim: Dict[str, Any], state: Dict[str, Any], trace: list[Any]) -> None:
        if not self.enabled:
            return
        sanitized_claim = {key: value for key, value in raw_claim.items() if key != "documents"}
        documents_summary = []
        for document in raw_claim.get("documents", []):
            if isinstance(document, dict):
                documents_summary.append(
                    {
                        "file_id": document.get("file_id"),
                        "document_type": document.get("actual_type") or document.get("document_type"),
                        "quality": document.get("quality"),
                    }
                )
        sanitized_claim["documents_summary"] = documents_summary
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO claim_results (
                        claim_id, member_id, policy_id, decision, approved_amount,
                        confidence_score, processing_status, degraded, claim_context,
                        policy_evaluation, financial_calculation, fraud_analysis, trace
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
                    ON CONFLICT (claim_id) DO UPDATE SET
                        decision = EXCLUDED.decision,
                        approved_amount = EXCLUDED.approved_amount,
                        confidence_score = EXCLUDED.confidence_score,
                        processing_status = EXCLUDED.processing_status,
                        degraded = EXCLUDED.degraded,
                        claim_context = EXCLUDED.claim_context,
                        policy_evaluation = EXCLUDED.policy_evaluation,
                        financial_calculation = EXCLUDED.financial_calculation,
                        fraud_analysis = EXCLUDED.fraud_analysis,
                        trace = EXCLUDED.trace
                    """,
                    (
                        claim_id,
                        raw_claim.get("member_id"),
                        raw_claim.get("policy_id"),
                        state.get("result").decision if state.get("result") else None,
                        state.get("result").approved_amount if state.get("result") else None,
                        state.get("result").confidence_score if state.get("result") else None,
                        state.get("result").processing_status if state.get("result") else "COMPLETED",
                        bool(state.get("degraded", False)),
                        json.dumps(_json_ready(sanitized_claim), default=str),
                        json.dumps(_json_ready(state.get("policy_evaluation_result")), default=str),
                        json.dumps(_json_ready(state.get("financials_result")), default=str),
                        json.dumps(_json_ready(state.get("fraud_result")), default=str),
                        json.dumps(_json_ready(trace), default=str),
                    ),
                )
            connection.commit()