from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from .config import config


@dataclass
class LLMRequest:
    prompt: str
    metadata: Dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    metadata: Dict[str, Any]


@dataclass
class VisionRequest:
    document_bytes: Optional[bytes] = None
    document_path: Optional[str] = None
    mime_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VisionResponse:
    text: str
    structured: Dict[str, Any]
    metadata: Dict[str, Any]


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


class VisionProvider(ABC):
    @abstractmethod
    def analyze(self, request: VisionRequest) -> VisionResponse:
        raise NotImplementedError


@contextmanager
def _temporary_document_path(document_bytes: bytes, suffix: str = ".bin") -> Iterator[str]:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        handle.write(document_bytes)
        handle.flush()
        handle.close()
        yield handle.name
    finally:
        try:
            Path(handle.name).unlink(missing_ok=True)
        except Exception:
            pass


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, temperature: float):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def generate(self, request: LLMRequest) -> LLMResponse:
        try:
            from google import genai
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("google-genai is not installed") from exc

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=request.prompt,
        )
        text = getattr(response, "text", "") or ""
        return LLMResponse(text=text, metadata={"model": self.model, **request.metadata})


class GeminiVisionProvider(VisionProvider):
    def __init__(self, api_key: str, model: str, temperature: float):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def analyze(self, request: VisionRequest) -> VisionResponse:
        try:
            from google import genai
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("google-genai is not installed") from exc

        client = genai.Client(api_key=self.api_key)
        if request.document_path:
            with open(request.document_path, "rb") as fh:
                document_bytes = fh.read()
        elif request.document_bytes is not None:
            document_bytes = request.document_bytes
        else:
            document_bytes = b""

        if document_bytes:
            with _temporary_document_path(document_bytes) as temp_path:
                _ = temp_path

        response = client.models.generate_content(
            model=self.model,
            contents=request.metadata or {},
        )
        text = getattr(response, "text", "") or ""
        return VisionResponse(text=text, structured={}, metadata={"model": self.model, **(request.metadata or {})})


@dataclass
class ProviderSet:
    llm: Optional[LLMProvider] = None
    vision: Optional[VisionProvider] = None


def build_provider_set() -> ProviderSet:
    if not config.gemini_api_key:
        return ProviderSet()
    return ProviderSet(
        llm=GeminiLLMProvider(config.gemini_api_key, config.gemini_model, config.gemini_temperature),
        vision=GeminiVisionProvider(config.gemini_api_key, config.gemini_ocr_model, config.gemini_temperature),
    )