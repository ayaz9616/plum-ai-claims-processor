from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional

from .config import config
from .temp_documents import temporary_document_path


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


class GeminiLLMProvider(LLMProvider):
    # NOTE: temperature/top_p/top_k are deprecated for Gemini 3.5/3.6 Flash and are
    # intentionally NOT sent to the API. GEMINI_TEMPERATURE is kept in the environment
    # for backward compatibility but is not forwarded.
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

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
    # NOTE: temperature/top_p/top_k are deprecated for Gemini 3.5/3.6 Flash and are
    # intentionally NOT sent to the API. GEMINI_TEMPERATURE is kept in the environment
    # for backward compatibility but is not forwarded.
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def analyze(self, request: VisionRequest) -> VisionResponse:
        try:
            from google import genai
            from google.genai import types
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

        mime_type = request.mime_type or "application/pdf"
        prompt = "Please transcribe this document and provide a basic understanding."
        if request.metadata and "prompt" in request.metadata:
            prompt = request.metadata["prompt"]

        try:
            if document_bytes:
                contents = [
                    types.Part.from_bytes(data=document_bytes, mime_type=mime_type),
                    prompt
                ]
            else:
                contents = [prompt]

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")

        text = getattr(response, "text", "") or ""
        # Keep provider-native structured data at the boundary when it is available.
        # The adapter remains responsible for validation and fallback parsing.
        structured = getattr(response, "parsed", None)
        if not isinstance(structured, dict):
            structured = {}
        return VisionResponse(text=text, structured=structured, metadata={"model": self.model, **(request.metadata or {})})


@dataclass
class ProviderSet:
    llm: Optional[LLMProvider] = None
    vision: Optional[VisionProvider] = None


def build_provider_set() -> ProviderSet:
    llm = None
    vision = None

    if config.gemini_llm_api_key:
        llm = GeminiLLMProvider(config.gemini_llm_api_key, config.gemini_model)
    if config.gemini_ocr_api_key:
        vision = GeminiVisionProvider(config.gemini_ocr_api_key, config.gemini_ocr_model)

    return ProviderSet(llm=llm, vision=vision)
