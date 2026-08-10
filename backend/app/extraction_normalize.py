"""Normalize provider document extraction output before StructuredDocumentData validation."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas import StructuredDocumentData

MONEY_FIELDS = (
    "total",
    "subtotal",
    "tax",
    "discount",
    "other_charges",
    "grand_total",
    "amount_payable",
    "amount_received",
)

LINE_ITEM_MONEY_FIELDS = ("amount", "unit_price", "price", "total", "approved_amount", "network_discount", "copay")

_CURRENCY_PATTERN = re.compile(
    r"(?:₹|\$|€|£|¥|Rs\.?|INR|USD|EUR|GBP)\s*",
    re.IGNORECASE,
)


class DocumentExtractionNormalizationError(ValueError):
    """Raised when provider extraction output cannot be safely normalized."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


def normalize_money(value: Any, *, field: str = "amount") -> Optional[Decimal]:
    """Parse a monetary value to Decimal without using float arithmetic."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise DocumentExtractionNormalizationError(
            f"invalid monetary value for {field}: boolean", field=field
        )
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"null", "none", "n/a", "-", ""}:
            return None
        cleaned = _CURRENCY_PATTERN.sub("", cleaned)
        cleaned = cleaned.replace(",", "").strip()
        cleaned = re.sub(r"\s+", "", cleaned)
        if not cleaned:
            return None
        if not re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
            raise DocumentExtractionNormalizationError(
                f"malformed monetary value {value!r} for {field}", field=field
            )
        try:
            return Decimal(cleaned)
        except InvalidOperation as exc:
            raise DocumentExtractionNormalizationError(
                f"malformed monetary value {value!r} for {field}", field=field
            ) from exc
    raise DocumentExtractionNormalizationError(
        f"unsupported monetary type {type(value).__name__} for {field}", field=field
    )


def normalize_treatment(value: Any) -> Optional[str]:
    """Collapse list-shaped treatments into a deterministic string."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                part = item.strip()
            elif isinstance(item, dict):
                part = str(
                    item.get("description")
                    or item.get("name")
                    or item.get("procedure")
                    or item.get("treatment")
                    or ""
                ).strip()
            else:
                part = str(item).strip()
            if part:
                parts.append(part)
        if not parts:
            return None
        return "; ".join(parts)
    text = str(value).strip()
    return text or None


def normalize_confidence(value: Any) -> Decimal:
    """Preserve provider confidence without inflating or defaulting valid values."""
    if value is None:
        return Decimal("0.5")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return Decimal("0.5")
        try:
            return Decimal(cleaned)
        except InvalidOperation as exc:
            raise DocumentExtractionNormalizationError(
                f"malformed confidence value {value!r}", field="confidence"
            ) from exc
    raise DocumentExtractionNormalizationError(
        f"unsupported confidence type {type(value).__name__}", field="confidence"
    )


def normalize_line_items(items: Any) -> List[Dict[str, Any]]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise DocumentExtractionNormalizationError("line_items must be a list", field="line_items")
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise DocumentExtractionNormalizationError(
                f"line_items[{index}] must be an object", field="line_items"
            )
        entry = dict(item)
        for money_key in LINE_ITEM_MONEY_FIELDS:
            if money_key in entry:
                entry[money_key] = normalize_money(entry[money_key], field=f"line_items[{index}].{money_key}")
        normalized.append(entry)
    return normalized


def verify_financial_consistency(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect contradictory monetary fields after normalization."""
    mismatches: List[Dict[str, Any]] = []
    items = payload.get("line_items") or []
    if items:
        line_sum = sum(
            (item.get("amount") or Decimal("0"))
            for item in items
            if isinstance(item, dict) and item.get("amount") is not None
        )
        for total_field in ("amount_payable", "grand_total", "total", "subtotal"):
            stated = payload.get(total_field)
            if stated is not None and line_sum != stated:
                mismatches.append(
                    {
                        "field": "bill_total",
                        "total_field": total_field,
                        "line_item_total": str(line_sum),
                        "stated_total": str(stated),
                        "reason": "line items do not sum to document total",
                    }
                )
                break

    header_totals = {
        field: payload[field]
        for field in ("subtotal", "grand_total", "amount_received", "total", "amount_payable")
        if payload.get(field) is not None
    }
    unique_header_values = set(header_totals.values())
    if len(unique_header_values) > 1:
        mismatches.append(
            {
                "field": "financial_totals",
                "values": {key: str(value) for key, value in header_totals.items()},
                "reason": "document contains conflicting financial totals",
            }
        )
    return mismatches


def normalize_structured_document_payload(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Normalize provider payload to StructuredDocumentData-compatible primitives."""
    payload = dict(raw)

    payload["treatment"] = normalize_treatment(payload.get("treatment"))
    payload["line_items"] = normalize_line_items(payload.get("line_items"))

    for field in MONEY_FIELDS:
        if field in payload:
            payload[field] = normalize_money(payload.get(field), field=field)

    if "confidence" in payload:
        payload["confidence"] = normalize_confidence(payload.get("confidence"))

    mismatches = verify_financial_consistency(payload)
    return payload, mismatches


def parse_structured_document(raw: Dict[str, Any]) -> Tuple[StructuredDocumentData, List[Dict[str, Any]]]:
    """Normalize provider output and validate against StructuredDocumentData."""
    payload, mismatches = normalize_structured_document_payload(raw)
    try:
        parsed = StructuredDocumentData.model_validate(payload)
    except Exception as exc:
        raise DocumentExtractionNormalizationError(
            f"normalized extraction failed schema validation: {exc}"
        ) from exc
    return parsed, mismatches
