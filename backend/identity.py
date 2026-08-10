"""Shared identity normalization for document and policy checks."""

from __future__ import annotations

import re
import unicodedata


def normalize_identity_name(name: str) -> str:
    """Canonical, conservative identity comparison for OCR/document variations."""
    name = unicodedata.normalize("NFKC", str(name or ""))
    name = re.sub(r"^(mr|ms|mrs|dr)\.?\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s]", " ", name.casefold())
    return " ".join(name.split())
