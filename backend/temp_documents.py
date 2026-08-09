from __future__ import annotations

import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class TempDocumentHandle:
    path: Path
    filename: str
    content_type: str
    size_bytes: int


@contextmanager
def temporary_document_path(document_bytes: bytes, suffix: str) -> Iterator[Path]:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    path = Path(handle.name)
    try:
        handle.write(document_bytes)
        handle.flush()
        handle.close()
        yield path
    finally:
        try:
            handle.close()
        except Exception:
            pass
        path.unlink(missing_ok=True)
