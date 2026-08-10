from typing import Dict, Any, List
import json
from decimal import Decimal
from backend.app.schemas import DocumentExtraction, DocumentArtifact, DocumentClassification, NormalizedDocument
from backend.app.infrastructure.providers import ProviderSet
from backend.app.errors import ExtractionError
from backend.app.extraction_normalize import parse_structured_document


class DocumentExtractor:
    def extract(self, documents: List[NormalizedDocument]) -> List[DocumentExtraction]:
        extracted: List[DocumentExtraction] = []
        for document in documents:
            extracted.append(
                DocumentExtraction(
                    file_id=document.file_id,
                    document_type=document.document_type,
                    extracted=document.extracted,
                    confidence=Decimal("0.95") if document.quality != "UNREADABLE" else Decimal("0.30"),
                )
            )
        return extracted


